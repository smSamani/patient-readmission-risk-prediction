from __future__ import annotations

from typing import Any

from app.database import fetch_all, fetch_one, get_connection, row_to_dict
from app.services.lab_report_service import get_lab_report_patient_ids
from app.utils.display_formatting import add_display_age_fields, add_display_label_fields, format_display_label
from app.utils.errors import not_found

USER_INTERVENTION_STATUSES = ("planned", "in_progress", "completed", "cancelled")
_STATUS_PLACEHOLDERS = ", ".join("?" for _ in USER_INTERVENTION_STATUSES)

QUEUE_SORT_COLUMNS = {
    "patient_id": "patient_id",
    "patient_name": "patient_name",
    "age": "age",
    "gender": "gender",
    "primary_diagnosis_group": "primary_diagnosis_group",
    "admission_source": "admission_source",
    "discharge_destination": "discharge_destination",
    "calibrated_risk_pct": "calibrated_risk_pct",
    "risk_category": "risk_category",
}


def _clean_limit(limit: int) -> int:
    return min(max(limit, 1), 100)


def list_patients(filters: dict[str, Any]) -> dict[str, Any]:
    where: list[str] = []
    params: list[Any] = []
    joins: list[str] = []

    def ensure_join(join_sql: str) -> None:
        if join_sql not in joins:
            joins.append(join_sql)

    exact_filters = {
        "risk_category": "pq.risk_category",
        "gender": "pq.gender",
        "primary_diagnosis_group": "pq.primary_diagnosis_group",
        "admission_source": "pq.admission_source",
        "discharge_destination": "pq.discharge_destination",
    }
    for input_name, column in exact_filters.items():
        value = filters.get(input_name)
        if value:
            where.append(f"{column} = ?")
            params.append(value)

    if filters.get("min_risk") is not None:
        where.append("pq.calibrated_risk_pct >= ?")
        params.append(filters["min_risk"])
    if filters.get("max_risk") is not None:
        where.append("pq.calibrated_risk_pct <= ?")
        params.append(filters["max_risk"])
    if filters.get("search"):
        where.append("(pq.patient_id LIKE ? OR pq.patient_name LIKE ? OR CAST(pq.encounter_id AS TEXT) LIKE ?)")
        term = f"%{filters['search']}%"
        params.extend([term, term, term])

    if filters.get("min_age") is not None:
        ensure_join("JOIN patients p ON p.patient_id = pq.patient_id")
        where.append("p.age_numeric >= ?")
        params.append(filters["min_age"])
        
    if filters.get("max_age") is not None:
        ensure_join("JOIN patients p ON p.patient_id = pq.patient_id")
        where.append("p.age_numeric <= ?")
        params.append(filters["max_age"])

    if filters.get("race"):
        ensure_join("JOIN patients p ON p.patient_id = pq.patient_id")
        where.append("p.race = ?")
        params.append(filters["race"])

    if filters.get("primary_physician"):
        ensure_join("JOIN synthetic_context sc ON sc.encounter_id = pq.encounter_id")
        where.append("sc.primary_physician LIKE ?")
        params.append(f"%{filters['primary_physician']}%")

    if filters.get("ward_unit"):
        ensure_join("JOIN synthetic_context sc ON sc.encounter_id = pq.encounter_id")
        where.append("sc.ward_unit LIKE ?")
        params.append(f"%{filters['ward_unit']}%")

    if filters.get("room_number"):
        ensure_join("JOIN synthetic_context sc ON sc.encounter_id = pq.encounter_id")
        where.append("sc.room_number LIKE ?")
        params.append(f"%{filters['room_number']}%")

    if filters.get("min_time_in_hospital") is not None:
        ensure_join("JOIN encounters e ON e.encounter_id = pq.encounter_id")
        where.append("e.time_in_hospital >= ?")
        params.append(filters["min_time_in_hospital"])

    if filters.get("max_time_in_hospital") is not None:
        ensure_join("JOIN encounters e ON e.encounter_id = pq.encounter_id")
        where.append("e.time_in_hospital <= ?")
        params.append(filters["max_time_in_hospital"])

    if filters.get("duplicate_first_name"):
        where.append(
            """
            substr(pq.patient_name, 1, instr(pq.patient_name || ' ', ' ') - 1) IN (
                SELECT first_name FROM (
                    SELECT substr(patient_name, 1, instr(patient_name || ' ', ' ') - 1) AS first_name,
                           COUNT(*) AS first_name_count
                    FROM patient_queue
                    GROUP BY first_name
                    HAVING first_name_count > 1
                )
            )
            """
        )

    if filters.get("first_name"):
        where.append("substr(pq.patient_name, 1, instr(pq.patient_name || ' ', ' ') - 1) = ?")
        params.append(filters["first_name"])

    has_lab_report = filters.get("has_lab_report")
    if has_lab_report is not None:
        lab_report_ids = get_lab_report_patient_ids(filters)
        if lab_report_ids:
            placeholders = ", ".join("?" for _ in lab_report_ids)
            operator = "IN" if has_lab_report else "NOT IN"
            where.append(f"pq.patient_id {operator} ({placeholders})")
            params.extend(sorted(lab_report_ids))
        elif has_lab_report:
            where.append("1 = 0")

    joins_sql = " ".join(joins)
    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    
    sort_by = QUEUE_SORT_COLUMNS.get(filters.get("sort_by") or "calibrated_risk_pct", "calibrated_risk_pct")
    if sort_by in QUEUE_SORT_COLUMNS:
        sort_by = f"pq.{sort_by}"
        
    sort_order = "ASC" if str(filters.get("sort_order", "desc")).lower() == "asc" else "DESC"
    limit = _clean_limit(int(filters.get("limit") or 20))
    offset = max(int(filters.get("offset") or 0), 0)

    count_query = f"""
        SELECT COUNT(DISTINCT pq.patient_id) AS total 
        FROM patient_queue pq
        {joins_sql}
        {where_sql}
    """
    total_row = fetch_one(count_query, params)
    
    rows_query = f"""
        SELECT DISTINCT pq.patient_id, pq.encounter_id, pq.model_row_id, pq.patient_name, pq.age, pq.gender,
               pq.primary_diagnosis_group, pq.admission_source, pq.discharge_destination,
               pq.calibrated_risk_pct, pq.risk_category
        FROM patient_queue pq
        {joins_sql}
        {where_sql}
        ORDER BY {sort_by} {sort_order}, pq.patient_id ASC
        LIMIT ? OFFSET ?
    """
    rows = fetch_all(rows_query, [*params, limit, offset])
    
    items = []
    for row in rows:
        item = dict(row)
        add_display_age_fields(item, stable_key_field="patient_id")
        add_display_label_fields(
            item,
            [
                "gender",
                "primary_diagnosis_group",
                "admission_source",
                "discharge_destination",
                "risk_category",
            ],
        )
        item["view_digital_chart_url"] = f"/patients/{item['patient_id']}"
        items.append(item)
    return {"items": items, "total": int(total_row["total"]), "limit": limit, "offset": offset}


def get_patient_keys(patient_id: str) -> dict[str, Any]:
    row = fetch_one(
        "SELECT patient_id, encounter_id, model_row_id FROM patient_queue WHERE patient_id = ?",
        [patient_id],
    )
    if row is None:
        raise not_found("Patient not found")
    return dict(row)


def get_patient_chart(patient_id: str) -> dict[str, Any]:
    keys = get_patient_keys(patient_id)
    encounter_id = keys["encounter_id"]

    row = fetch_one(
        """
        SELECT p.patient_id, p.patient_nbr, p.patient_name, p.mrn, p.gender, p.race, p.age, p.age_numeric,
               e.encounter_id, e.model_row_id, e.admission_type_group, e.admission_source_group, e.discharge_group,
               e.time_in_hospital, e.num_lab_procedures, e.num_procedures, e.num_medications,
               e.number_outpatient, e.number_emergency, e.number_inpatient, e.prior_utilization_total,
               e.utilization_level, e.number_diagnoses, e.clinical_burden_level,
               e.diag_1_group, e.diag_2_group, e.diag_3_group, e.A1Cresult, e.hba1c_tested,
               e.max_glu_serum, e.max_glu_tested, e.insulin, e.change, e.diabetesMed,
               r.actual_readmitted_30d, r.predicted_probability_calibrated, r.calibrated_risk_pct,
               r.risk_category, r.predicted_class,
               s.primary_physician, s.ward_unit, s.room_number, s.scheduled_discharge_date,
               s.scheduled_discharge_time, s.discharge_planner, s.clinical_summary_note,
               s.social_context_note, s.care_transition_note
        FROM patients p
        JOIN encounters e ON e.patient_id = p.patient_id
        LEFT JOIN risk_predictions r ON r.encounter_id = e.encounter_id
        LEFT JOIN synthetic_context s ON s.encounter_id = e.encounter_id
        WHERE p.patient_id = ?
        """,
        [patient_id],
    )
    if row is None:
        raise not_found("Patient not found")
    data = dict(row)
    add_display_age_fields(data, stable_key_field="patient_id")

    review = row_to_dict(fetch_one("SELECT * FROM clinical_reviews WHERE encounter_id = ?", [encounter_id])) or {}
    add_display_label_fields(
        review,
        [
            "primary_diagnosis_group",
            "secondary_diagnosis_group",
            "third_diagnosis_group",
            "diabetes_medication_used",
            "insulin",
            "medication_change_during_stay",
            "medication_reconciliation_status",
            "diabetes_education_status",
        ],
    )
    top3 = [dict(r) for r in fetch_all("SELECT rank, feature, feature_label, feature_value, shap_value, effect_direction FROM shap_top3 WHERE encounter_id = ? ORDER BY rank ASC", [encounter_id])]
    interventions = []
    for intervention_row in fetch_all(
        f"""
        SELECT * FROM interventions
        WHERE encounter_id = ? AND intervention_status IN ({_STATUS_PLACEHOLDERS})
        ORDER BY created_at DESC, intervention_id ASC
        """,
        [encounter_id, *USER_INTERVENTION_STATUSES],
    ):
        intervention = dict(intervention_row)
        intervention["source_type"] = "user_saved"
        intervention["is_user_created"] = True
        intervention["is_editable"] = True
        interventions.append(intervention)
    timeline = [dict(r) for r in fetch_all("SELECT * FROM diagnosis_timeline WHERE encounter_id = ? ORDER BY diagnosis_rank ASC", [encounter_id])]

    diagnosis_note = None
    if data.get("number_diagnoses") and int(data["number_diagnoses"]) > 3:
        diagnosis_note = f"Total diagnoses recorded: {data['number_diagnoses']}. Only the top 3 structured diagnosis groups are available in this demo dataset."

    return {
        "patient_id": patient_id,
        "encounter_id": encounter_id,
        "model_row_id": keys["model_row_id"],
        "box_1_demographics_encounter": {
            "patient_identity": {
                "patient_name": data.get("patient_name"),
                "mrn": data.get("mrn"),
                "primary_physician": data.get("primary_physician"),
                "ward_unit": data.get("ward_unit"),
                "room_number": data.get("room_number"),
                "risk_category": format_display_label(data.get("risk_category")),
                "risk_category_raw": data.get("risk_category"),
            },
            "demographics": {
                "age": data.get("display_age"),
                "display_age": data.get("display_age"),
                "age_band": data.get("age_band"),
                "age_numeric": data.get("age_numeric"),
                "gender": format_display_label(data.get("gender")),
                "gender_raw": data.get("gender"),
                "race": format_display_label(data.get("race")),
                "race_raw": data.get("race"),
            },
            "encounter_context": {
                "admission_type": format_display_label(data.get("admission_type_group")),
                "admission_type_raw": data.get("admission_type_group"),
                "admission_source": format_display_label(data.get("admission_source_group")),
                "admission_source_raw": data.get("admission_source_group"),
                "discharge_destination": format_display_label(data.get("discharge_group")),
                "discharge_destination_raw": data.get("discharge_group"),
                "time_in_hospital": data.get("time_in_hospital"),
                "scheduled_discharge_date": data.get("scheduled_discharge_date"),
                "scheduled_discharge_time": data.get("scheduled_discharge_time"),
                "discharge_planner": data.get("discharge_planner"),
            },
        },
        "box_2_clinical_snapshot": {
            "prior_utilization": {
                "prior_inpatient_visits": data.get("number_inpatient"),
                "prior_emergency_visits": data.get("number_emergency"),
                "prior_outpatient_visits": data.get("number_outpatient"),
                "total_prior_utilization": data.get("prior_utilization_total"),
                "utilization_level": data.get("utilization_level"),
            },
            "current_admission_burden": {
                "diagnoses_recorded": data.get("number_diagnoses"),
                "active_medications": data.get("num_medications"),
                "lab_procedures": data.get("num_lab_procedures"),
                "procedures": data.get("num_procedures"),
                "clinical_burden_level": data.get("clinical_burden_level"),
            },
            "visualization_data": {
                "utilization_chart": [
                    {"label": "Inpatient", "value": data.get("number_inpatient") or 0},
                    {"label": "Emergency", "value": data.get("number_emergency") or 0},
                    {"label": "Outpatient", "value": data.get("number_outpatient") or 0},
                ]
            },
        },
        "box_3_clinical_review": {
            "labs_glycemic_monitoring": {
                "hba1c_result_status": review.get("hba1c_result_status") or data.get("A1Cresult"),
                "hba1c_tested": review.get("hba1c_tested", data.get("hba1c_tested")),
                "max_glucose_result_status": review.get("max_glucose_result_status") or data.get("max_glu_serum"),
                "max_glu_tested": review.get("max_glu_tested", data.get("max_glu_tested")),
                "lab_procedures_count": review.get("lab_procedures_count", data.get("num_lab_procedures")),
                "last_lab_review_timestamp": review.get("last_lab_review_timestamp"),
                "reviewed_by": review.get("lab_reviewed_by"),
            },
            "medication_review": {
                "diabetes_medication_used": review.get("diabetes_medication_used") or format_display_label(data.get("diabetesMed")),
                "diabetes_medication_used_raw": review.get("diabetes_medication_used_raw") or data.get("diabetesMed"),
                "insulin_status": review.get("insulin") or format_display_label(data.get("insulin")),
                "insulin_status_raw": review.get("insulin_raw") or data.get("insulin"),
                "medication_change_during_stay": review.get("medication_change_during_stay") or format_display_label(data.get("change")),
                "medication_change_during_stay_raw": review.get("medication_change_during_stay_raw") or data.get("change"),
                "active_medication_count": review.get("active_medication_count", data.get("num_medications")),
                "key_diabetes_medications": review.get("key_diabetes_medications"),
                "medication_reconciliation_status": review.get("medication_reconciliation_status"),
                "diabetes_education_status": review.get("diabetes_education_status"),
                "reviewed_by_pharmacist": review.get("reviewed_by_pharmacist"),
            },
            "diagnosis_review": {
                "primary_diagnosis": review.get("primary_diagnosis_group") or format_display_label(data.get("diag_1_group")),
                "primary_diagnosis_raw": review.get("primary_diagnosis_group_raw") or data.get("diag_1_group"),
                "secondary_diagnosis": review.get("secondary_diagnosis_group") or format_display_label(data.get("diag_2_group")),
                "secondary_diagnosis_raw": review.get("secondary_diagnosis_group_raw") or data.get("diag_2_group"),
                "third_diagnosis": review.get("third_diagnosis_group") or format_display_label(data.get("diag_3_group")),
                "third_diagnosis_raw": review.get("third_diagnosis_group_raw") or data.get("diag_3_group"),
                "total_diagnoses_recorded": review.get("total_diagnoses_recorded", data.get("number_diagnoses")),
                "diagnosis_timeline": timeline,
                "diagnosis_limitation_note": diagnosis_note,
            },
        },
        "risk_prediction": {
            "calibrated_risk_pct": data.get("calibrated_risk_pct"),
            "predicted_probability_calibrated": data.get("predicted_probability_calibrated"),
            "risk_category": format_display_label(data.get("risk_category")),
            "risk_category_raw": data.get("risk_category"),
            "predicted_class": data.get("predicted_class"),
            "actual_readmitted_30d": data.get("actual_readmitted_30d"),
        },
        "shap_top3": top3,
        "interventions": interventions,
        "synthetic_context": {
            "clinical_summary_note": data.get("clinical_summary_note"),
            "social_context_note": data.get("social_context_note"),
            "care_transition_note": data.get("care_transition_note"),
        },
    }


def get_summary() -> dict[str, Any]:
    with get_connection() as conn:
        counts = {row["risk_category"]: row["count"] for row in conn.execute("SELECT risk_category, COUNT(*) AS count FROM risk_predictions GROUP BY risk_category")}
        total = conn.execute("SELECT COUNT(*) AS count FROM patient_queue").fetchone()["count"]
        avg = conn.execute("SELECT AVG(calibrated_risk_pct) AS value FROM risk_predictions").fetchone()["value"]
        missing_hba1c = conn.execute("SELECT COUNT(*) AS count FROM encounters WHERE hba1c_tested = 0").fetchone()["count"]
        dx_rows = conn.execute("SELECT primary_diagnosis_group, COUNT(*) AS count FROM patient_queue GROUP BY primary_diagnosis_group ORDER BY count DESC LIMIT 5").fetchall()
    return {
        "total_demo_patients": total,
        "high_risk_count": counts.get("High Risk", 0),
        "medium_risk_count": counts.get("Medium Risk", 0),
        "low_risk_count": counts.get("Low Risk", 0),
        "average_calibrated_risk_pct": round(avg or 0, 2),
        "patients_missing_hba1c": missing_hba1c,
        "top_primary_diagnosis_groups": [dict(r) for r in dx_rows],
    }
