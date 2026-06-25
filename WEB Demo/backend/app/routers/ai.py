from __future__ import annotations

import logging
import json
import os
import re
from difflib import SequenceMatcher
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from app.database import fetch_all, fetch_one
from app.services.lab_report_service import get_lab_report_capabilities, get_lab_report_manifest
from app.services.patient_service import get_patient_chart, list_patients

router = APIRouter(prefix="/ai", tags=["ai"])

# Logger config
logger = logging.getLogger("app.ai")

GEMINI_API_KEYS = [
    key
    for key in [
        os.getenv("GEMINI_API_KEY"),
        os.getenv("GEMINI_API_KEY_1"),
        os.getenv("GEMINI_API_KEY_2"),
        os.getenv("GEMINI_API_KEY_3"),
        os.getenv("GEMINI_API_KEY_4"),
        os.getenv("GEMINI_API_KEY_5"),
        os.getenv("GOOGLE_API_KEY"),
    ]
    if key
]

GEMINI_MODELS = [
    "gemini-3.1-flash-lite",
]

class RouteRequest(BaseModel):
    prompt: str

class RouteResponse(BaseModel):
    route: str
    patient_id: str | None = None
    filters: dict[str, Any] | None = None


FILTER_KEYS = {
    "risk_category",
    "gender",
    "primary_diagnosis_group",
    "admission_source",
    "discharge_destination",
    "search",
    "min_age",
    "max_age",
    "min_time_in_hospital",
    "max_time_in_hospital",
    "duplicate_first_name",
    "first_name",
    "race",
    "primary_physician",
    "ward_unit",
    "room_number",
    "has_lab_report",
    "lab_report_type",
    "lab_report_status",
    "lab_report_source_basis",
    "min_risk",
    "max_risk",
}


FILTER_ALIASES = {
    "attending_physician": "primary_physician",
    "physician": "primary_physician",
    "doctor": "primary_physician",
    "provider": "primary_physician",
    "ward": "ward_unit",
    "unit": "ward_unit",
    "room": "room_number",
    "age_min": "min_age",
    "age_max": "max_age",
    "minimum_age": "min_age",
    "maximum_age": "max_age",
    "min_los": "min_time_in_hospital",
    "max_los": "max_time_in_hospital",
    "min_stay": "min_time_in_hospital",
    "max_stay": "max_time_in_hospital",
    "source": "admission_source",
    "admission": "admission_source",
    "destination": "discharge_destination",
    "diagnosis": "primary_diagnosis_group",
}


def _compact_patient_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "patient_id": item.get("patient_id"),
        "patient_name": item.get("patient_name"),
        "age": item.get("display_age"),
        "age_band": item.get("age_band"),
        "gender": item.get("gender"),
        "primary_diagnosis_group": item.get("primary_diagnosis_group"),
        "admission_source": item.get("admission_source"),
        "discharge_destination": item.get("discharge_destination"),
        "calibrated_risk_pct": item.get("calibrated_risk_pct"),
        "risk_category": item.get("risk_category"),
        "view_digital_chart_url": item.get("view_digital_chart_url"),
    }


def _canonicalize_admission_source(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = _normalize_name_text(value).replace("-", " ").replace("_", " ")
    if any(term in normalized for term in ["er", "emergency room", "emergency department", "urgent"]):
        return "Emergency_Room"
    if "referral" in normalized:
        return "Referral"
    if "transfer" in normalized:
        return "Transfer_Other"
    return value


def _canonicalize_risk_category(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = _normalize_name_text(value)
    if "high" in normalized:
        return "High Risk"
    if "medium" in normalized or "moderate" in normalized:
        return "Medium Risk"
    if "low" in normalized:
        return "Low Risk"
    return value


def _canonicalize_gender(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = _normalize_name_text(value)
    if normalized in {"male", "man", "men", "mard", "agha", "aghaye"}:
        return "Male"
    if normalized in {"female", "woman", "women", "zan", "khanom"}:
        return "Female"
    return value


def _canonicalize_physician(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    matched = _match_physician_filter(_normalize_name_text(value))
    return matched or value


def _normalize_filter_aliases(raw: dict[str, Any] | None) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in (raw or {}).items():
        canonical_key = FILTER_ALIASES.get(key, key)
        normalized[canonical_key] = value
    if "primary_physician" in normalized:
        normalized["primary_physician"] = _canonicalize_physician(normalized["primary_physician"])
    if "admission_source" in normalized:
        normalized["admission_source"] = _canonicalize_admission_source(normalized["admission_source"])
    if "risk_category" in normalized:
        normalized["risk_category"] = _canonicalize_risk_category(normalized["risk_category"])
    if "gender" in normalized:
        normalized["gender"] = _canonicalize_gender(normalized["gender"])
    return normalized


def _clean_tool_filters(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = _normalize_filter_aliases(raw)
    filters = {key: value for key, value in raw.items() if key in FILTER_KEYS and value not in (None, "", "all")}
    filters["limit"] = min(max(int(raw.get("limit") or 20), 1), 100)
    filters["offset"] = max(int(raw.get("offset") or 0), 0)
    filters["sort_by"] = raw.get("sort_by") or "calibrated_risk_pct"
    filters["sort_order"] = raw.get("sort_order") or "desc"
    return filters


def _tool_get_data_capabilities(args: dict[str, Any]) -> dict[str, Any]:
    rows = fetch_all("""
        SELECT
            MIN(p.age_numeric) AS min_age,
            MAX(p.age_numeric) AS max_age,
            MIN(e.time_in_hospital) AS min_time_in_hospital,
            MAX(e.time_in_hospital) AS max_time_in_hospital
        FROM patient_queue pq
        JOIN patients p ON p.patient_id = pq.patient_id
        JOIN encounters e ON e.encounter_id = pq.encounter_id
    """)
    distinct_rows = fetch_all("""
        SELECT 'risk_category' AS field, risk_category AS value FROM patient_queue GROUP BY risk_category
        UNION ALL
        SELECT 'gender' AS field, gender AS value FROM patient_queue GROUP BY gender
        UNION ALL
        SELECT 'primary_diagnosis_group' AS field, primary_diagnosis_group AS value FROM patient_queue GROUP BY primary_diagnosis_group
        UNION ALL
        SELECT 'admission_source' AS field, admission_source AS value FROM patient_queue GROUP BY admission_source
        UNION ALL
        SELECT 'discharge_destination' AS field, discharge_destination AS value FROM patient_queue GROUP BY discharge_destination
        UNION ALL
        SELECT 'primary_physician' AS field, primary_physician AS value FROM synthetic_context WHERE primary_physician IS NOT NULL GROUP BY primary_physician
        UNION ALL
        SELECT 'ward_unit' AS field, ward_unit AS value FROM synthetic_context WHERE ward_unit IS NOT NULL GROUP BY ward_unit
        UNION ALL
        SELECT 'room_number' AS field, room_number AS value FROM synthetic_context WHERE room_number IS NOT NULL GROUP BY room_number
    """)
    values: dict[str, list[str]] = {}
    for row in distinct_rows:
        values.setdefault(row["field"], []).append(row["value"])
    ranges = dict(rows[0]) if rows else {}
    return {
        "supported_views": ["queue", "chart"],
        "supported_filters": sorted(FILTER_KEYS),
        "filter_values": values,
        "numeric_ranges": ranges,
        "lab_reports": get_lab_report_capabilities(),
    }


def _tool_search_patient_records(args: dict[str, Any]) -> dict[str, Any]:
    filters = _clean_tool_filters(args.get("filters") if "filters" in args else args)
    result = list_patients(filters)
    return {
        "filters_used": {key: value for key, value in filters.items() if key in FILTER_KEYS},
        "total": result["total"],
        "sample": [_compact_patient_item(item) for item in result["items"][:12]],
    }


def _tool_find_patient_candidates(args: dict[str, Any]) -> dict[str, Any]:
    query = _normalize_name_text(str(args.get("query") or args.get("text") or ""))
    tokens = [token for token in query.split() if len(token) > 1]
    rows = fetch_all("""
        SELECT pq.patient_id, pq.patient_name, pq.gender, p.age_numeric, pq.risk_category,
               pq.primary_diagnosis_group, pq.admission_source, pq.discharge_destination,
               sc.primary_physician, sc.ward_unit, sc.room_number
        FROM patient_queue pq
        JOIN patients p ON p.patient_id = pq.patient_id
        LEFT JOIN synthetic_context sc ON sc.encounter_id = pq.encounter_id
        ORDER BY pq.patient_id
    """)
    candidates = []
    for row in rows:
        haystack = _normalize_name_text(" ".join(str(row[key] or "") for key in row.keys()))
        score = SequenceMatcher(None, query, haystack).ratio() if query else 0.0
        token_hits = sum(1 for token in tokens if token in haystack)
        if token_hits or score >= 0.28:
            candidates.append({
                "patient_id": row["patient_id"],
                "patient_name": row["patient_name"],
                "age": row["age_numeric"],
                "gender": row["gender"],
                "risk_category": row["risk_category"],
                "primary_diagnosis_group": row["primary_diagnosis_group"],
                "admission_source": row["admission_source"],
                "discharge_destination": row["discharge_destination"],
                "primary_physician": row["primary_physician"],
                "ward_unit": row["ward_unit"],
                "room_number": row["room_number"],
                "match_score": round(score + (token_hits * 0.18), 3),
            })
    candidates.sort(key=lambda item: item["match_score"], reverse=True)
    return {"query": query, "total_candidates": len(candidates), "candidates": candidates[:12]}


def _tool_get_patient_context(args: dict[str, Any]) -> dict[str, Any]:
    patient_id = str(args.get("patient_id") or "").strip()
    if not patient_id and args.get("query"):
        candidates = _tool_find_patient_candidates({"query": args["query"]}).get("candidates", [])
        if candidates:
            patient_id = candidates[0]["patient_id"]
    if not patient_id:
        return {"error": "patient_id or query is required"}
    try:
        chart = get_patient_chart(patient_id)
    except Exception as exc:
        return {"error": str(exc), "patient_id": patient_id}

    identity = chart.get("box_1_demographics_encounter", {}).get("patient_identity", {})
    demographics = chart.get("box_1_demographics_encounter", {}).get("demographics", {})
    encounter = chart.get("box_1_demographics_encounter", {}).get("encounter_context", {})
    labs = chart.get("box_3_clinical_review", {}).get("labs_glycemic_monitoring", {})
    meds = chart.get("box_3_clinical_review", {}).get("medication_review", {})
    risk = chart.get("risk_prediction", {})
    return {
        "patient_id": chart.get("patient_id"),
        "patient_name": identity.get("patient_name"),
        "mrn": identity.get("mrn"),
        "age": demographics.get("display_age"),
        "gender": demographics.get("gender"),
        "primary_physician": identity.get("primary_physician"),
        "ward_unit": identity.get("ward_unit"),
        "room_number": identity.get("room_number"),
        "time_in_hospital": encounter.get("time_in_hospital"),
        "scheduled_discharge": f"{encounter.get('scheduled_discharge_date')} {encounter.get('scheduled_discharge_time')}",
        "discharge_destination": encounter.get("discharge_destination"),
        "risk_category": risk.get("risk_category"),
        "calibrated_risk_pct": risk.get("calibrated_risk_pct"),
        "labs": labs,
        "medication_review": meds,
    }


def _tool_inspect_lab_report_index(args: dict[str, Any]) -> dict[str, Any]:
    report_type = str(args.get("report_type") or args.get("lab_report_type") or "").upper()
    patient_id = str(args.get("patient_id") or "").strip()
    rows = []
    for row in get_lab_report_manifest():
        if report_type and row.get("report_type") != report_type:
            continue
        if patient_id and row.get("patient_id") != patient_id:
            continue
        rows.append(row)
    return {
        "total": len(rows),
        "reports": rows[:40],
        "capabilities": get_lab_report_capabilities(),
    }


AGENT_TOOLS = {
    "get_data_capabilities": _tool_get_data_capabilities,
    "search_patient_records": _tool_search_patient_records,
    "find_patient_candidates": _tool_find_patient_candidates,
    "get_patient_context": _tool_get_patient_context,
    "inspect_lab_report_index": _tool_inspect_lab_report_index,
}


def _parse_int(value: str) -> int:
    return int(value.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")))


def _normalize_name_text(value: str) -> str:
    normalized = value.lower().strip()
    normalized = re.sub(r"[^a-z0-9\s-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _match_physician_filter(msg: str) -> str | None:
    rows = fetch_all("""
        SELECT DISTINCT primary_physician
        FROM synthetic_context
        WHERE primary_physician IS NOT NULL
        ORDER BY primary_physician
    """)
    tokens = set(re.sub(r"[^a-z0-9\s-]", " ", msg.lower()).split())
    physician_context = any(term in msg for term in ["dr ", "doctor", "physician", "provider", "cases", "patient"])
    for row in rows:
        physician = row["primary_physician"]
        normalized = _normalize_name_text(physician)
        parts = normalized.split()
        last_name = parts[-1] if parts else ""
        if normalized in msg or (physician_context and last_name and last_name in tokens):
            return physician
    return None


def deterministic_patient_route(prompt: str) -> dict[str, Any] | None:
    """
    Route patient-specific questions to the chart before the LLM has a chance to
    turn a name into a broad queue search.
    """
    msg = _normalize_name_text(prompt)
    if not msg:
        return None
    if any(term in msg for term in ["dr ", "doctor", "physician", "provider"]):
        return None

    cohort_terms = [
        "patients",
        "mariz hayi",
        "mariza",
        "same first name",
        "duplicate",
    ]
    if any(term in msg for term in cohort_terms) and not any(term in msg for term in ["mr ", "mrs ", "ms ", "aghaye", "khanom"]):
        return None

    rows = fetch_all("""
        SELECT patient_id, patient_name, gender
        FROM patient_queue
        ORDER BY patient_id
    """)
    patients = []
    for row in rows:
        name = row["patient_name"]
        parts = _normalize_name_text(name).split()
        if not parts:
            continue
        patients.append({
            "patient_id": row["patient_id"],
            "name": name,
            "normalized": _normalize_name_text(name),
            "first": parts[0],
            "last": parts[-1],
            "gender": (row["gender"] or "").lower(),
        })

    for patient in patients:
        if patient["normalized"] in msg or patient["patient_id"].lower() in msg:
            return {"route": "chart", "patient_id": patient["patient_id"], "filters": None}

    requested_gender = None
    if any(term in msg for term in ["mr ", "mister", "aghaye", "agha", "male"]):
        requested_gender = "male"
    elif any(term in msg for term in ["mrs ", "ms ", "miss ", "khanom", "female"]):
        requested_gender = "female"

    tokens = set(msg.split())
    if requested_gender:
        last_matches = [
            patient for patient in patients
            if patient["last"] in tokens and patient["gender"] == requested_gender
        ]
        if len(last_matches) == 1:
            return {"route": "chart", "patient_id": last_matches[0]["patient_id"], "filters": None}

    unique_token_matches = [
        patient for patient in patients
        if patient["first"] in tokens or patient["last"] in tokens
    ]
    if len(unique_token_matches) == 1:
        return {"route": "chart", "patient_id": unique_token_matches[0]["patient_id"], "filters": None}

    # Forgive small spelling slips in full-name prompts, e.g. "Oliva Patel".
    best_patient = None
    best_score = 0.0
    for patient in patients:
        score = SequenceMatcher(None, patient["normalized"], msg).ratio()
        last_name_present = patient["last"] in tokens
        if last_name_present and score > best_score:
            best_patient = patient
            best_score = score
    if best_patient and best_score >= 0.58:
        return {"route": "chart", "patient_id": best_patient["patient_id"], "filters": None}

    return None


def deterministic_route(prompt: str) -> dict[str, Any] | None:
    """
    Handle high-frequency dashboard queries deterministically before LLM routing.
    This keeps numeric ranges, length-of-stay filters, and cohort grouping stable.
    """
    msg = prompt.lower().strip()
    msg = re.sub(r"\s+", " ", msg)
    filters: dict[str, Any] = {}
    age_context_terms = ["age", "ages", "aged", "year", "years", "old", "sen", "senn", "saal", "سن", "سال"]

    if re.search(r"\b(male|men|man)\b", msg) or any(term in msg for term in ["agha", "aghaye", "mard", "مرد"]):
        filters["gender"] = "Male"
    elif re.search(r"\b(female|women|woman)\b", msg) or any(term in msg for term in ["khanom", "zan", "زن", "خانم"]):
        filters["gender"] = "Female"

    lab_terms = [
        "lab report",
        "lab result",
        "lab results",
        "laboratory report",
        "laboratory result",
        "azmayesh",
        "azmayeshgah",
        "آزمایش",
        "نتیجه آزمایش",
    ]
    if any(term in msg for term in lab_terms):
        negative_terms = ["without", "no lab", "no report", "nadaran", "ندارن", "ندارد", "بدون"]
        filters["has_lab_report"] = not any(term in msg for term in negative_terms)
        if any(term in msg for term in ["a1c", "hba1c", "hemoglobin a1c", "hemoglobin a1c"]):
            filters["lab_report_type"] = "HBA1C"
        elif any(term in msg for term in ["glucose", "blood sugar", "max serum glucose", "sugar", "ghand", "قند"]):
            filters["lab_report_type"] = "GLUCOSE"
        if any(term in msg for term in ["high", "بالا"]):
            filters["lab_report_status"] = "High"
        elif any(term in msg for term in ["elevated"]):
            filters["lab_report_status"] = "Elevated"

    physician = _match_physician_filter(msg)
    if physician:
        filters["primary_physician"] = physician

    # Age ranges: "between 20 and 50", "20 to 50", Finglish/Persian "20 ta 50".
    age_range_patterns = [
        r"(?:age|ages|aged|sen|senn|senesh(?:oon)?|سن)\D{0,24}([0-9۰-۹٠-٩]{1,3})\D{0,12}(?:to|ta|taa|and|-|تا|الی|بین)\D{0,12}([0-9۰-۹٠-٩]{1,3})",
        r"(?:between|bein|beyn|بین)\D{0,18}([0-9۰-۹٠-٩]{1,3})\D{0,12}(?:and|to|ta|taa|-|تا|الی)\D{0,12}([0-9۰-۹٠-٩]{1,3})",
        r"([0-9۰-۹٠-٩]{1,3})\D{0,12}(?:to|ta|taa|and|-|تا|الی)\D{0,12}([0-9۰-۹٠-٩]{1,3})\D{0,24}(?:age|ages|aged|years?|old|sen|senn|saal|سن|سال)",
    ]
    for pattern in age_range_patterns:
        match = re.search(pattern, msg)
        if match and any(term in msg for term in age_context_terms):
            first = _parse_int(match.group(1))
            second = _parse_int(match.group(2))
            filters["min_age"] = min(first, second)
            filters["max_age"] = max(first, second)
            break

    if "min_age" not in filters:
        match = re.search(r"(?:over|older than|above|bishtar az|بیشتر از|بالای)\D{0,16}([0-9۰-۹٠-٩]{1,3})", msg)
        if match and any(term in msg for term in ["age", "aged", "sen", "senn", "سن", "saal", "سال"]):
            filters["min_age"] = _parse_int(match.group(1))
        match = re.search(r"(?:under|younger than|below|less than|kamtar az|کمتر از|زیر)\D{0,16}([0-9۰-۹٠-٩]{1,3})", msg)
        if match and any(term in msg for term in ["age", "aged", "sen", "senn", "سن", "saal", "سال"]):
            filters["max_age"] = _parse_int(match.group(1))

    # Admission source aliases. Keep this deterministic because ER wording is common.
    if any(phrase in msg for phrase in [
        "from the er",
        "from er",
        "via er",
        "came from er",
        "came from the er",
        "emergency room",
        "emergency department",
        "admitted from er",
        "admitted via er",
        "az er",
        "orjansi",
        "اورژانس",
    ]):
        filters["admission_source"] = "Emergency_Room"

    room_match = re.search(r"(?:room(?: number| no| nbr|#)?|otagh|اتاق)\D{0,10}([0-9]{1,2}[a-z]-[0-9]{2,4}|[0-9]{1,4}[a-z]?|[a-z]-?[0-9]{2,4})", msg, re.IGNORECASE)
    if room_match:
        filters["room_number"] = room_match.group(1).upper()

    ward_match = re.search(
        r"(?:ward|unit|bakhsh|بخش)\D{0,10}([a-z][a-z\s]{2,28}?(?:ward|unit)?)"
        r"(?=\s+(?:and|va|with|ke|که|hast|are|risk|patients|mariz|room|otagh)|$)",
        msg,
        re.IGNORECASE,
    )
    if ward_match:
        ward = re.sub(r"\s+", " ", ward_match.group(1)).strip()
        if ward and ward not in {"risk", "patients", "mariz"}:
            filters["ward_unit"] = ward.title()

    # Length of stay: "more than 3 days", "bishtar az 3 rooz", "over 3 days".
    stay_terms = ["day", "days", "rooz", "روز", "hospital", "stay", "bastari", "بستری", "inja", "اینجا"]
    stay_more = re.search(r"(?:more than|over|longer than|greater than|above|bishtar az|بیشتر از|بالای)\D{0,16}([0-9۰-۹٠-٩]{1,2})", msg)
    if stay_more and any(term in msg for term in stay_terms):
        filters["min_time_in_hospital"] = _parse_int(stay_more.group(1)) + 1
    stay_at_least = re.search(r"(?:at least|minimum| حداقل)\D{0,16}([0-9۰-۹٠-٩]{1,2})", msg)
    if stay_at_least and any(term in msg for term in stay_terms):
        filters["min_time_in_hospital"] = _parse_int(stay_at_least.group(1))
    stay_less = re.search(r"(?:less than|under|below|shorter than|kamtar az|کمتر از|زیر)\D{0,16}([0-9۰-۹٠-٩]{1,2})", msg)
    if stay_less and any(term in msg for term in stay_terms):
        filters["max_time_in_hospital"] = _parse_int(stay_less.group(1)) - 1

    # Duplicate first names / same first name cohort query.
    if any(phrase in msg for phrase in [
        "same first name",
        "duplicate first name",
        "shared first name",
        "first name repeated",
        "esm yeki",
        "esme yeki",
        "ham esm",
        "هم اسم",
        "اسم مشترک",
    ]):
        filters["duplicate_first_name"] = True

    # Risk ranges.
    risk_range = re.search(r"(?:risk|ریسک)\D{0,24}([0-9۰-۹٠-٩]{1,3})\D{0,12}(?:to|ta|taa|and|-|تا|الی)\D{0,12}([0-9۰-۹٠-٩]{1,3})", msg)
    if risk_range:
        first = _parse_int(risk_range.group(1))
        second = _parse_int(risk_range.group(2))
        filters["min_risk"] = min(first, second)
        filters["max_risk"] = max(first, second)

    if not filters:
        return None
    return {"route": "queue", "filters": filters}

def get_cohort_metadata() -> str:
    """
    Fetch denormalized metadata of all 100 patients to provide context for the router.
    This allows the model to match names, physicians, age bands, etc. directly.
    """
    rows = fetch_all("""
        SELECT DISTINCT 
            pq.patient_id, 
            pq.patient_name, 
            p.age, 
            pq.gender, 
            sc.primary_physician, 
            p.race, 
            pq.calibrated_risk_pct, 
            pq.risk_category, 
            pq.primary_diagnosis_group, 
            pq.admission_source,
            pq.discharge_destination,
            sc.ward_unit,
            sc.room_number
        FROM patient_queue pq
        JOIN patients p ON p.patient_id = pq.patient_id
        LEFT JOIN synthetic_context sc ON sc.encounter_id = pq.encounter_id
    """)
    
    metadata = []
    for row in rows:
        metadata.append({
            "patient_id": row["patient_id"],
            "patient_name": row["patient_name"],
            "age_band": row["age"],
            "gender": row["gender"],
            "primary_physician": row["primary_physician"],
            "ward_unit": row["ward_unit"],
            "room_number": row["room_number"],
            "race": row["race"],
            "calibrated_risk_pct": row["calibrated_risk_pct"],
            "risk_category": row["risk_category"],
            "primary_diagnosis_group": row["primary_diagnosis_group"],
            "admission_source": row["admission_source"],
            "discharge_destination": row["discharge_destination"]
        })
        
    return json.dumps(metadata, indent=2)


def get_router_data_capabilities() -> str:
    return json.dumps({
        "lab_reports": get_lab_report_capabilities(),
    }, indent=2)


async def _call_gemini_json(payload: dict[str, Any]) -> dict[str, Any]:
    if not GEMINI_API_KEYS:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key is not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY.",
        )

    last_error = None
    for model in GEMINI_MODELS:
        for idx, api_key in enumerate(GEMINI_API_KEYS):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
                        parsed = json.loads(text_out)
                        logger.info("Gemini agent response via model=%s key=%s: %s", model, idx + 1, parsed)
                        return parsed
                    if res.status_code == 429:
                        last_error = f"429 quota on {model} key {idx + 1}"
                        logger.warning(last_error)
                    else:
                        last_error = f"Status {res.status_code}: {res.text[:250]}"
                        logger.warning("Gemini model=%s key=%s failed: %s", model, idx + 1, last_error)
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Gemini model=%s key=%s raised exception: %s", model, idx + 1, last_error)
    raise HTTPException(status_code=502, detail=f"All Gemini API keys and models exhausted. Last error: {last_error}")


def _agent_system_prompt() -> str:
    return """
You are the agentic routing brain for the Patient Discharge Portal.

The user may write in English, Persian, or Finglish. Understand the intent, but all internal reasoning summaries and final route explanations must be in English.

Your job:
1. Decide whether the user is asking for a cohort/list of patients or a specific patient's digital case.
2. Use tools before making that decision. You are not allowed to answer from memory.
3. If the request is cohort/list oriented, inspect data capabilities and/or search patient records, then return route="queue" with the filters that reproduce the cohort in the list view.
4. If the request is about one specific patient, resolve the patient through tools, then return route="chart" with patient_id. The frontend will open that Digital Chart and pass the original prompt into the chart copilot.
5. If the user asks for patients with data that lives outside SQLite, such as lab reports, inspect the relevant file/index tool and then return data-backed filters.

Available tools:
- get_data_capabilities(args): returns supported filters, cohort value ranges, and file-backed data capabilities.
- search_patient_records(args): searches SQLite-backed patient queue with supported filters. Args may include {"filters": {...}}.
- find_patient_candidates(args): resolves possible patient identities from names, IDs, clinicians, locations, or loose text.
- get_patient_context(args): fetches a compact Digital Chart context for one patient by patient_id or query.
- inspect_lab_report_index(args): reads the lab report manifest/index. Args may include report_type, lab_report_type, patient_id.

Important:
- Prefer tool evidence over assumptions.
- Do not hardcode examples from prompt suggestions.
- Do not route to a prior patient unless tools identify that patient for the current user prompt.
- Return queue filters only from supported filters.
"""


def _parse_tool_args(call: dict[str, Any]) -> dict[str, Any]:
    if isinstance(call.get("args"), dict):
        return call["args"]
    args_json = call.get("args_json")
    if isinstance(args_json, str) and args_json.strip():
        try:
            parsed = json.loads(args_json)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def _normalize_tool_calls(prompt: str, calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for call in calls:
        tool_name = call.get("tool_name")
        if tool_name not in AGENT_TOOLS:
            continue
        args = _parse_tool_args(call)
        if tool_name in {"find_patient_candidates", "get_patient_context"} and not (args.get("query") or args.get("patient_id")):
            args["query"] = prompt
        normalized.append({"tool_name": tool_name, "args": args})
    return normalized[:5]


async def _agent_plan_tool_calls(prompt: str, observations: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    observation_text = ""
    if observations:
        observation_text = "\nPrevious tool observations:\n" + json.dumps(observations, ensure_ascii=False)[:12000]
    payload = {
        "contents": [{"role": "user", "parts": [{"text": f"User prompt: {prompt}{observation_text}"}]}],
        "systemInstruction": {"parts": [{"text": _agent_system_prompt() + """
Choose the next read-only tools to call.

Tool argument examples:
- For "Olivia Patel ready for discharge": [{"tool_name":"find_patient_candidates","args_json":"{\"query\":\"Olivia Patel\"}"}]
- For "patients aged 60-80 from ER": [{"tool_name":"search_patient_records","args_json":"{\"filters\":{\"min_age\":60,\"max_age\":80,\"admission_source\":\"Emergency_Room\",\"limit\":100}}"}]
- For "Dr Carter male patients aged 30-50 from ER": first use get_data_capabilities if you need the exact physician name, then search_patient_records with the exact physician value.
- For "patients with lab report": [{"tool_name":"inspect_lab_report_index","args_json":"{}"},{"tool_name":"search_patient_records","args_json":"{\"filters\":{\"has_lab_report\":true,\"limit\":100}}"}]

Do not leave args_json empty for patient candidate or patient search tools.
If previous observations are sufficient and no more tools are needed, return an empty tool_calls array.
Return tool_calls only.
"""}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "reasoning_summary": {"type": "STRING"},
                    "tool_calls": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "tool_name": {
                                    "type": "STRING",
                                    "enum": list(AGENT_TOOLS.keys()),
                                },
                                "args_json": {"type": "STRING"},
                            },
                            "required": ["tool_name", "args_json"],
                        },
                    },
                },
                "required": ["tool_calls"],
            },
        },
    }
    parsed = await _call_gemini_json(payload)
    calls = parsed.get("tool_calls") or []
    return _normalize_tool_calls(prompt, calls)


def _execute_agent_tool_calls(tool_calls: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observations = []
    for call in tool_calls:
        tool_name = call.get("tool_name")
        args = call.get("args") or {}
        tool = AGENT_TOOLS.get(tool_name)
        if tool is None:
            continue
        try:
            result = tool(args)
        except Exception as exc:
            result = {"error": str(exc)}
        observations.append({
            "tool_name": tool_name,
            "args": args,
            "result": result,
        })
    return observations


def _observed_patient_candidates(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for observation in observations:
        result = observation.get("result") or {}
        if observation.get("tool_name") == "find_patient_candidates":
            candidates.extend(result.get("candidates") or [])
        elif observation.get("tool_name") == "get_patient_context" and result.get("patient_id"):
            candidates.append({
                "patient_id": result.get("patient_id"),
                "patient_name": result.get("patient_name"),
                "match_score": 1.0,
            })
    candidates.sort(key=lambda item: float(item.get("match_score") or 0), reverse=True)
    return candidates


def _observed_queue_searches(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    searches = []
    for observation in observations:
        if observation.get("tool_name") != "search_patient_records":
            continue
        result = observation.get("result") or {}
        filters = result.get("filters_used") or {}
        searches.append({
            "filters": filters,
            "total": int(result.get("total") or 0),
        })
    searches.sort(key=lambda item: (item["total"] > 0, len(item["filters"]), -item["total"]), reverse=True)
    return searches


def _prompt_mentions_filter_family(prompt: str, key: str) -> bool:
    msg = _normalize_name_text(prompt)
    checks = {
        "risk_category": ["risk", "high risk", "medium risk", "low risk", "risky", "khatar", "ریسک"],
        "ward_unit": ["ward", "unit", "bakhsh", "cardiology", "endocrinology", "respiratory", "renal", "urology", "orthopaedic", "gastroenterology", "medicine", "بخش"],
        "gender": ["male", "female", "man", "woman", "men", "women", "mard", "zan", "agha", "aghaye", "khanom", "مرد", "زن", "خانم"],
        "primary_diagnosis_group": ["diagnosis", "disease", "diabetes", "circulatory", "neoplasm", "injury", "respiratory", "digestive", "genitourinary", "musculoskeletal"],
        "race": ["race", "caucasian", "africanamerican", "african american", "hispanic"],
        "discharge_destination": ["destination", "home", "nursing", "facility", "transfer", "discharge to", "tarkhis be"],
        "min_risk": ["risk", "%", "percent"],
        "max_risk": ["risk", "%", "percent"],
    }
    return any(term in msg for term in checks.get(key, []))


def _explicit_prompt_filters(prompt: str) -> dict[str, Any]:
    route = deterministic_route(prompt)
    if not route:
        return {}
    return _normalize_filter_aliases(route.get("filters") or {})


def _ground_queue_filters(
    prompt: str,
    model_filters: dict[str, Any] | None,
    observations: list[dict[str, Any]],
) -> dict[str, Any] | None:
    searches = [search for search in _observed_queue_searches(observations) if search["total"] > 0]
    grounded = dict(searches[0]["filters"]) if searches else {}
    if not grounded and model_filters:
        grounded = dict(model_filters)

    grounded = _normalize_filter_aliases(grounded)
    explicit = _explicit_prompt_filters(prompt)
    if explicit:
        grounded.update(explicit)

    # The model may overfit to one sample patient and add risk/ward/gender labels
    # that were never requested. Keep those only when the prompt explicitly asks
    # for that filter family or the explicit parser extracted it.
    for key in [
        "risk_category",
        "ward_unit",
        "gender",
        "primary_diagnosis_group",
        "race",
        "discharge_destination",
        "min_risk",
        "max_risk",
    ]:
        if key in grounded and key not in explicit and not _prompt_mentions_filter_family(prompt, key):
            grounded.pop(key, None)

    cleaned = {key: value for key, value in grounded.items() if key in FILTER_KEYS and value not in (None, "", "all")}
    if not cleaned:
        return None
    return cleaned


async def _agent_finalize_route(prompt: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{
                    "text": json.dumps({
                        "user_prompt": prompt,
                        "tool_observations": observations,
                    }, ensure_ascii=False)
                }],
            }
        ],
        "systemInstruction": {"parts": [{"text": _agent_system_prompt() + "\nFinal step: use the tool observations to return the route JSON for the frontend. Do not ask for more information unless no route is possible."}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "route": {"type": "STRING", "enum": ["queue", "chart"]},
                    "patient_id": {"type": "STRING"},
                    "filters": {
                        "type": "OBJECT",
                        "properties": {
                            "risk_category": {"type": "STRING", "enum": ["High Risk", "Medium Risk", "Low Risk"]},
                            "gender": {"type": "STRING", "enum": ["Male", "Female"]},
                            "primary_diagnosis_group": {"type": "STRING", "enum": ["Other", "Diabetes", "Circulatory", "Neoplasms", "Injury", "Respiratory", "Digestive", "Genitourinary", "Musculoskeletal"]},
                            "admission_source": {"type": "STRING", "enum": ["Referral", "Emergency_Room", "Transfer_Other"]},
                            "discharge_destination": {"type": "STRING", "enum": ["Home", "Nursing_Facility_or_Transfer", "Other"]},
                            "min_age": {"type": "INTEGER"},
                            "max_age": {"type": "INTEGER"},
                            "min_time_in_hospital": {"type": "INTEGER"},
                            "max_time_in_hospital": {"type": "INTEGER"},
                            "duplicate_first_name": {"type": "BOOLEAN"},
                            "first_name": {"type": "STRING"},
                            "race": {"type": "STRING", "enum": ["Caucasian", "AfricanAmerican", "Hispanic"]},
                            "primary_physician": {"type": "STRING"},
                            "ward_unit": {"type": "STRING"},
                            "room_number": {"type": "STRING"},
                            "has_lab_report": {"type": "BOOLEAN"},
                            "lab_report_type": {"type": "STRING", "enum": ["HBA1C", "GLUCOSE"]},
                            "lab_report_status": {"type": "STRING"},
                            "lab_report_source_basis": {"type": "STRING", "enum": ["A1Cresult", "max_glu_serum"]},
                            "min_risk": {"type": "NUMBER"},
                            "max_risk": {"type": "NUMBER"},
                            "search": {"type": "STRING"},
                        },
                    },
                    "confidence": {"type": "NUMBER"},
                    "explanation": {"type": "STRING"},
                },
                "required": ["route"],
            },
        },
    }
    parsed = await _call_gemini_json(payload)
    route = parsed.get("route")
    if route not in {"queue", "chart"}:
        raise HTTPException(status_code=502, detail="Agent returned an invalid route.")

    filters = parsed.get("filters") or None
    if filters:
        filters = _normalize_filter_aliases(filters)
        filters = {key: value for key, value in filters.items() if key in FILTER_KEYS and value not in (None, "", "all")}

    patient_id = parsed.get("patient_id") or None
    if route == "chart":
        exists = fetch_one("SELECT patient_id FROM patient_queue WHERE patient_id = ?", [patient_id]) if patient_id else None
        if not exists:
            candidates = _observed_patient_candidates(observations)
            if candidates:
                patient_id = candidates[0]["patient_id"]
                exists = fetch_one("SELECT patient_id FROM patient_queue WHERE patient_id = ?", [patient_id])
        if not patient_id or not exists:
            raise HTTPException(status_code=502, detail="Agent selected chart route without an observed valid patient_id.")
        return {"route": "chart", "patient_id": patient_id, "filters": None}

    filters = _ground_queue_filters(prompt, filters, observations)

    if filters:
        check_filters = {**filters, "limit": 1, "offset": 0}
        try:
            checked_total = list_patients(check_filters)["total"]
        except Exception:
            checked_total = 0
        if checked_total == 0:
            searches = _observed_queue_searches(observations)
            usable = [search for search in searches if search["total"] > 0]
            if usable:
                filters = _ground_queue_filters(prompt, usable[0]["filters"], observations)

    if not filters:
        searches = _observed_queue_searches(observations)
        usable = [search for search in searches if search["total"] > 0]
        if usable:
            filters = _ground_queue_filters(prompt, usable[0]["filters"], observations)

    return {"route": "queue", "patient_id": None, "filters": filters}


async def agentic_route_clinical_query(prompt: str) -> dict[str, Any]:
    tool_calls = await _agent_plan_tool_calls(prompt)
    if not tool_calls:
        tool_calls = [{"tool_name": "get_data_capabilities", "args": {}}]
    observations = _execute_agent_tool_calls(tool_calls)
    follow_up_calls = await _agent_plan_tool_calls(prompt, observations)
    if follow_up_calls:
        observations.extend(_execute_agent_tool_calls(follow_up_calls))
    return await _agent_finalize_route(prompt, observations)

@router.post("/route", response_model=RouteResponse)
async def route_clinical_query(req: RouteRequest) -> dict:
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    return await agentic_route_clinical_query(prompt)
