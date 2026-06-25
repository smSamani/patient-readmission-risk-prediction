from __future__ import annotations

from typing import Any
from app.database import fetch_all
from app.services.patient_service import get_patient_chart


def evaluate_patient_copilot(patient_id: str) -> dict[str, Any]:
    chart = get_patient_chart(patient_id)
    encounter_id = chart["encounter_id"]

    # Fetch all SHAP features
    shap_rows = fetch_all(
        "SELECT feature, feature_label, feature_value, shap_value, effect_direction FROM shap_all_features WHERE encounter_id = ?",
        [encounter_id],
    )
    shap_list = [dict(r) for r in shap_rows]

    # Keywords for matching SHAP features
    shap_keywords = {
        1: ["age", "inpatient", "emergency", "outpatient", "prior_utilization"],
        2: ["time_in_hospital", "diagnoses", "diag", "admission"],
        3: ["a1c", "glucose", "glu", "lab"],
        4: ["medication", "insulin", "metformin", "diabetesmed", "change"],
        5: ["discharge", "home", "transfer", "snf", "nursing"],
    }

    # Helper function to get SHAP context for each phase
    def get_shap_context_for_phase(phase_num: int) -> list[str]:
        keywords = shap_keywords[phase_num]
        phase_rows = []
        for row in shap_list:
            f_name = row.get("feature", "").lower()
            f_label = row.get("feature_label", "").lower()
            if any(kw in f_name or kw in f_label for kw in keywords):
                phase_rows.append(row)
        # Sort by absolute SHAP value descending
        phase_rows.sort(key=lambda r: abs(r.get("shap_value", 0.0)), reverse=True)
        context = []
        for row in phase_rows[:2]:
            val = row.get("shap_value", 0.0)
            if abs(val) > 0.01:
                direction = "risk-increasing" if val > 0 else "risk-decreasing"
                label = row.get("feature_label") or row.get("feature")
                context.append(f"The model explanation highlights {label} as a {direction} driver.")
        return context

    # 1. Phase 1: Historical Risk Profile
    p1_age = chart["box_1_demographics_encounter"]["demographics"]["age"]
    p1_inpatient = chart["box_2_clinical_snapshot"]["prior_utilization"]["prior_inpatient_visits"]
    p1_emergency = chart["box_2_clinical_snapshot"]["prior_utilization"]["prior_emergency_visits"]
    p1_outpatient = chart["box_2_clinical_snapshot"]["prior_utilization"]["prior_outpatient_visits"]
    p1_util_level = chart["box_2_clinical_snapshot"]["prior_utilization"]["utilization_level"]
    p1_risk_cat = chart["risk_prediction"]["risk_category"]
    p1_risk_pct = chart["risk_prediction"]["calibrated_risk_pct"]
    p1_util_total = chart["box_2_clinical_snapshot"]["prior_utilization"]["total_prior_utilization"]

    p1_evidence = [
        f"Age: {p1_age}",
        f"Prior inpatient visits: {p1_inpatient}",
        f"Prior utilization level: {p1_util_level}",
        f"Risk category: {p1_risk_cat}",
    ]

    if p1_inpatient >= 3 or p1_util_total >= 5 or p1_risk_cat == "High Risk":
        p1_status = "concern"
        p1_note = "The patient has repeated prior inpatient utilization, which supports a care-transition review before discharge."
    elif p1_inpatient >= 1 or p1_util_total >= 2 or p1_risk_cat == "Medium Risk":
        p1_status = "review"
        p1_note = "Historical healthcare utilization is moderate. Monitor post-discharge follow-up needs."
    else:
        p1_status = "clear"
        p1_note = "Low historical healthcare utilization indicates lower baseline risk."

    p1_shap_context = get_shap_context_for_phase(1)

    # 2. Phase 2: Current Encounter Complexity
    p2_adm_type = chart["box_1_demographics_encounter"]["encounter_context"]["admission_type"]
    p2_adm_source = chart["box_1_demographics_encounter"]["encounter_context"]["admission_source"]
    p2_time = chart["box_1_demographics_encounter"]["encounter_context"]["time_in_hospital"]
    p2_diagnoses = chart["box_3_clinical_review"]["diagnosis_review"]["total_diagnoses_recorded"]
    p2_diag_1 = chart["box_3_clinical_review"]["diagnosis_review"]["primary_diagnosis"]
    p2_diag_2 = chart["box_3_clinical_review"]["diagnosis_review"]["secondary_diagnosis"]
    p2_diag_3 = chart["box_3_clinical_review"]["diagnosis_review"]["third_diagnosis"]
    p2_burden = chart["box_2_clinical_snapshot"]["current_admission_burden"]["clinical_burden_level"]

    p2_evidence = [
        f"Admission type: {p2_adm_type}",
        f"Admission source: {p2_adm_source}",
        f"Time in hospital: {p2_time} days",
        f"Total diagnoses recorded: {p2_diagnoses}",
        f"Primary diagnosis: {p2_diag_1}",
        f"Secondary diagnosis: {p2_diag_2}",
        f"Third diagnosis: {p2_diag_3}",
        f"Clinical burden level: {p2_burden}",
    ]

    if p2_time >= 7 or p2_diagnoses >= 8 or p2_burden == "High":
        p2_status = "concern"
        p2_note = "Extended length of stay or high clinical burden indicates high encounter complexity. Ensure transition planning addresses all active diagnoses."
    elif p2_time >= 4 or p2_diagnoses >= 5 or p2_burden == "Medium":
        p2_status = "review"
        p2_note = "Moderate encounter complexity observed. Review discharge timing relative to diagnosis stability."
    else:
        p2_status = "clear"
        p2_note = "Encounter complexity metrics fall within typical baseline limits."

    p2_shap_context = get_shap_context_for_phase(2)

    # 3. Phase 3: Labs & Glycemic Review
    p3_labs_count = chart["box_3_clinical_review"]["labs_glycemic_monitoring"]["lab_procedures_count"]
    p3_hba1c_tested = chart["box_3_clinical_review"]["labs_glycemic_monitoring"]["hba1c_tested"]
    p3_hba1c_res = chart["box_3_clinical_review"]["labs_glycemic_monitoring"]["hba1c_result_status"]
    p3_glu_tested = chart["box_3_clinical_review"]["labs_glycemic_monitoring"]["max_glu_tested"]
    p3_glu_res = chart["box_3_clinical_review"]["labs_glycemic_monitoring"]["max_glucose_result_status"]

    p3_evidence = [
        f"Lab procedures count: {p3_labs_count}",
        f"HbA1c tested: {'Yes' if p3_hba1c_tested else 'No'}",
        f"HbA1c result: {p3_hba1c_res or 'Not Tested'}",
        f"Max glucose tested: {'Yes' if p3_glu_tested else 'No'}",
        f"Max glucose result: {p3_glu_res or 'Not Tested'}",
    ]

    is_diabetic_dx = any(x in str(diag).lower() for diag in [p2_diag_1, p2_diag_2, p2_diag_3] for x in ["diab", "glyc"])

    if not p3_hba1c_tested and (is_diabetic_dx or p1_risk_cat == "High Risk"):
        p3_status = "review"
        p3_note = "No structured HbA1c test recorded for this encounter. Consider ordering an HbA1c test if glycemic status is unknown."
    elif p3_hba1c_res in (">8", ">7", "High"):
        p3_status = "concern"
        p3_note = f"Suboptimal glycemic control indicated by elevated HbA1c ({p3_hba1c_res}). Ensure a clear monitoring plan is in place."
    elif p3_glu_res in (">200", ">300", "High"):
        p3_status = "concern"
        p3_note = f"Elevated inpatient glucose level ({p3_glu_res}) indicates active glycemic instability during the stay."
    else:
        p3_status = "clear"
        if p3_hba1c_res or p3_glu_res:
            p3_note = "Glycemic markers and HbA1c testing status are up to date and within acceptable limits."
        else:
            p3_note = "No HbA1c or max glucose measurements recorded during this encounter."

    p3_shap_context = get_shap_context_for_phase(3)

    # 4. Phase 4: Medication & Diabetes Regimen
    p4_med_count = chart["box_3_clinical_review"]["medication_review"]["active_medication_count"]
    p4_diab_med = chart["box_3_clinical_review"]["medication_review"]["diabetes_medication_used"]
    p4_insulin = chart["box_3_clinical_review"]["medication_review"]["insulin_status"]
    p4_change = chart["box_3_clinical_review"]["medication_review"]["medication_change_during_stay"]
    p4_key_meds = chart["box_3_clinical_review"]["medication_review"]["key_diabetes_medications"]
    p4_recon = chart["box_3_clinical_review"]["medication_review"]["medication_reconciliation_status"]
    p4_edu = chart["box_3_clinical_review"]["medication_review"]["diabetes_education_status"]
    p4_pharm = chart["box_3_clinical_review"]["medication_review"]["reviewed_by_pharmacist"]

    p4_evidence = [
        f"Active medication count: {p4_med_count}",
        f"Diabetes meds used: {p4_diab_med}",
        f"Insulin status: {p4_insulin}",
        f"Medication change during stay: {p4_change}",
        f"Key diabetes medications: {p4_key_meds or 'None'}",
        f"Medication reconciliation status: {p4_recon or 'Unknown'}",
        f"Diabetes education status: {p4_edu or 'Unknown'}",
        f"Reviewed by pharmacist: {p4_pharm or 'No'}",
    ]

    if p4_recon and "pending" in p4_recon.lower():
        p4_status = "concern"
        p4_note = "Confirm medication reconciliation status before discharge to prevent discrepancies."
    elif p4_edu and "recommended" in p4_edu.lower():
        p4_status = "review"
        p4_note = "Diabetes education is recommended but not yet documented as completed. Coordinate training before discharge."
    else:
        p4_status = "clear"
        p4_note = "Medication regimen has been reconciled and reviewed by pharmacy with no outstanding actions."

    p4_shap_context = get_shap_context_for_phase(4)

    # 5. Phase 5: Discharge Readiness & Care Transition
    p5_dest = chart["box_1_demographics_encounter"]["encounter_context"]["discharge_destination"]
    p5_date = chart["box_1_demographics_encounter"]["encounter_context"]["scheduled_discharge_date"]
    p5_time = chart["box_1_demographics_encounter"]["encounter_context"]["scheduled_discharge_time"]
    p5_planner = chart["box_1_demographics_encounter"]["encounter_context"]["discharge_planner"]
    p5_care_transition = chart["synthetic_context"]["care_transition_note"]
    p5_social = chart["synthetic_context"]["social_context_note"]

    p5_evidence = [
        f"Scheduled discharge date: {p5_date}",
        f"Scheduled discharge time: {p5_time}",
        f"Discharge planner: {p5_planner or 'Not Assigned'}",
        f"Discharge destination: {p5_dest}",
        f"Care transition note: {p5_care_transition or 'None'}",
        f"Social context note: {p5_social or 'None'}",
    ]

    if p1_risk_cat == "High Risk" and p5_dest == "Home":
        p5_status = "concern"
        p5_note = "The patient is planned for discharge home while categorized as high risk, so follow-up readiness and care-transition support should be reviewed before discharge."
    elif p1_risk_cat in ("High Risk", "Medium Risk") or p5_dest in (
        "Nursing Facility or Transfer",
        "Nursing Facility Or Transfer",
        "Other Transfer",
    ):
        p5_status = "review"
        p5_note = "Patient is transitioning to a nursing facility or requires care coordinate support. Verify facility acceptance and transport details."
    else:
        p5_status = "clear"
        p5_note = "Discharge plan and scheduled time appear aligned with low-risk patient status."

    p5_shap_context = get_shap_context_for_phase(5)

    # Dynamic key review items
    key_review_items = []
    if p1_status in ("concern", "review"):
        key_review_items.append("Review follow-up readiness due to high prior inpatient utilization.")
    if p2_status in ("concern", "review"):
        key_review_items.append("Review clinical stability and diagnosis timeline detail.")
    if p3_status in ("concern", "review"):
        key_review_items.append("Ensure glycemic monitoring is completed or order HbA1c before discharge.")
    if p4_status in ("concern", "review"):
        key_review_items.append("Confirm medication reconciliation status before discharge.")
    if p5_status in ("concern", "review"):
        key_review_items.append("Verify home care services or post-discharge transition support.")

    if not key_review_items:
        key_review_items.append("No critical actions pending. Standard care transition protocols apply.")

    # Overall assessment summary
    if p1_risk_cat == "High Risk":
        p_summary = f"This patient has high predicted readmission risk with prior inpatient visits and discharge planned to {p5_dest.lower()}."
    else:
        p_summary = f"This patient is stratified as {p1_risk_cat} ({p1_risk_pct}%) with prior utilization level {p1_util_level.lower()} and discharge planned to {p5_dest.lower()}."

    return {
        "patient_id": patient_id,
        "mode": "rule_based_prototype",
        "model_context_note": "This is a deterministic rule-based prototype using structured patient data, risk predictions, SHAP outputs, and available demo context. It is not a live LLM/RAG response.",
        "overall_assessment": {
            "risk_category": p1_risk_cat,
            "calibrated_risk_pct": p1_risk_pct,
            "summary": p_summary,
        },
        "phases": [
            {
                "phase_number": 1,
                "phase_name": "Historical Risk Profile",
                "status": p1_status,
                "evidence_used": p1_evidence,
                "shap_context": p1_shap_context,
                "copilot_note": p1_note,
            },
            {
                "phase_number": 2,
                "phase_name": "Current Encounter Complexity",
                "status": p2_status,
                "evidence_used": p2_evidence,
                "shap_context": p2_shap_context,
                "copilot_note": p2_note,
            },
            {
                "phase_number": 3,
                "phase_name": "Labs & Glycemic Review",
                "status": p3_status,
                "evidence_used": p3_evidence,
                "shap_context": p3_shap_context,
                "copilot_note": p3_note,
            },
            {
                "phase_number": 4,
                "phase_name": "Medication & Diabetes Regimen",
                "status": p4_status,
                "evidence_used": p4_evidence,
                "shap_context": p4_shap_context,
                "copilot_note": p4_note,
            },
            {
                "phase_number": 5,
                "phase_name": "Discharge Readiness & Care Transition",
                "status": p5_status,
                "evidence_used": p5_evidence,
                "shap_context": p5_shap_context,
                "copilot_note": p5_note,
            },
        ],
        "key_review_items": key_review_items,
        "data_limitations": [
            "This prototype uses structured demo data and precomputed SHAP outputs.",
            "It does not generate medical orders.",
            "It does not infer diagnoses beyond the top three structured diagnosis groups.",
        ],
    }


def translate_shap_context(shap_context: list[str]) -> list[str]:
    translated = []
    for item in shap_context:
        item_lower = item.lower()
        if "prior_inpatient_visits" in item_lower:
            translated.append("The model placed extra weight on this patient's prior inpatient hospitalizations.")
        elif "prior_emergency_visits" in item_lower:
            translated.append("The model placed extra weight on this patient's history of emergency department visits.")
        elif "prior_outpatient_visits" in item_lower:
            translated.append("The model noted the patient's frequency of outpatient visits.")
        elif "discharge_destination" in item_lower or "discharge_group" in item_lower or "discharge" in item_lower:
            translated.append("The planned discharge destination (e.g., facility vs. home) significantly influenced the risk prediction.")
        elif "hba1c" in item_lower or "a1c" in item_lower:
            translated.append("The patient's glycemic control status and HbA1c testing records were weighted by the model.")
        elif "glucose" in item_lower:
            translated.append("Peak glucose levels during the hospital stay impacted the readmission risk calculation.")
        elif "medication" in item_lower or "meds" in item_lower:
            translated.append("The total number or specific changes of diabetes medications during the stay served as an indicator of regimen complexity.")
        elif "insulin" in item_lower:
            translated.append("The active use of insulin or change in insulin regimen during this encounter was considered by the model.")
        elif "diagnoses" in item_lower or "diag" in item_lower:
            translated.append("The complexity and number of documented medical diagnoses contributed to the risk prediction.")
        elif "admission_source" in item_lower:
            translated.append("The source of hospital admission (e.g., emergency department) was identified as a risk factor.")
        elif "time_in_hospital" in item_lower:
            translated.append("The length of the hospital stay was a factor in the risk calculation.")
        elif "number_diagnoses" in item_lower:
            translated.append("The total count of recorded diagnoses influenced the complexity rating.")
        else:
            cleaned = item
            cleaned = cleaned.replace("prior_inpatient_visits", "prior inpatient visits")
            cleaned = cleaned.replace("prior_emergency_visits", "prior emergency visits")
            cleaned = cleaned.replace("prior_outpatient_visits", "prior outpatient visits")
            cleaned = cleaned.replace("discharge_destination", "discharge destination")
            cleaned = cleaned.replace("number_diagnoses", "number of diagnoses")
            cleaned = cleaned.replace("time_in_hospital", "time in hospital")
            cleaned = cleaned.replace("feature_value", "feature value")
            if "explanation highlights" in cleaned:
                cleaned = cleaned.replace("The model explanation highlights ", "The model highlighted the patient's ")
                cleaned = cleaned.replace(" as a risk-increasing driver.", " as a factor that increases readmission risk.")
                cleaned = cleaned.replace(" as a risk-decreasing driver.", " as a factor that decreases readmission risk.")
            translated.append(cleaned)
    return translated


def chat_patient_copilot(patient_id: str, message: str) -> dict[str, Any]:
    msg = message.lower().strip()

    # Get patient details/chart
    chart = get_patient_chart(patient_id)
    encounter_id = chart["encounter_id"]

    # Fetch all SHAP features
    shap_rows = fetch_all(
        "SELECT feature, feature_label, feature_value, shap_value, effect_direction FROM shap_all_features WHERE encounter_id = ?",
        [encounter_id],
    )
    shap_list = [dict(r) for r in shap_rows]

    # Helper to get matching SHAP context safely sorted
    def get_matching_shaps_safe(keywords: list[str]) -> list[str]:
        phase_rows = []
        for row in shap_list:
            f_name = row.get("feature", "").lower()
            f_label = row.get("feature_label", "").lower()
            if any(kw in f_name or kw in f_label for kw in keywords):
                phase_rows.append(row)
        # Sort by absolute SHAP value descending
        phase_rows.sort(key=lambda r: abs(r.get("shap_value", 0.0)), reverse=True)
        context = []
        for row in phase_rows[:2]:
            val = row.get("shap_value", 0.0)
            if abs(val) > 0.01:
                direction = "risk-increasing" if val > 0 else "risk-decreasing"
                label = row.get("feature_label") or row.get("feature")
                context.append(f"The model explanation highlights {label} as a {direction} driver.")
        return context

    # Helper for matching query keywords
    def match_any(keywords: list[str]) -> bool:
        return any(kw in msg for kw in keywords)

    demographics = chart["box_1_demographics_encounter"]["demographics"]
    identity = chart["box_1_demographics_encounter"]["patient_identity"]
    context = chart["box_1_demographics_encounter"]["encounter_context"]
    risk = chart["risk_prediction"]

    # ==========================================
    # 0. Basic Patient Facts Intent Layer
    # ==========================================

    # A. Patient Age
    if match_any(["how old", "patient age", "patient's age", "patient_age"]) or msg == "age?" or msg == "age":
        display_age = demographics.get("display_age")
        age_band = demographics.get("age_band")
        
        evidence_summary = []
        if display_age is not None:
            answer_markdown = f"This patient is **{display_age} years old**."
            evidence_summary.append(f"Display age: {display_age}")
            if age_band:
                answer_markdown += f" The original source age band is **{age_band}**."
                evidence_summary.append(f"Original age band: {age_band}")
        else:
            answer_markdown = "I do not have that field available for this demo patient."

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "patient_age",
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"The patient is {display_age} years old." if display_age else "Age is not available.",
            "evidence_summary": evidence_summary,
            "technical_evidence": {
                "structured_fields_used": ["display_age", "age", "age_numeric"],
                "shap_context": []
            },
            "follow_up_questions": [
                "What is this patient’s readmission risk?",
                "Where is this patient being discharged?",
                "Why is this patient high risk?"
            ],
            "limitations": [
                "This is a rule-based prototype using structured demo data."
            ]
        }

    # B. Patient Gender
    if match_any(["gender", "male or female", "male/female", "sex"]) or msg == "gender?":
        gender = demographics.get("gender")
        evidence_summary = []
        if gender:
            answer_markdown = f"This patient's gender is recorded as **{gender}**."
            evidence_summary.append(f"Gender: {gender}")
        else:
            answer_markdown = "I do not have that field available for this demo patient."

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "patient_gender",
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"The patient's gender is {gender}." if gender else "Gender is not available.",
            "evidence_summary": evidence_summary,
            "technical_evidence": {
                "structured_fields_used": ["gender", "gender_raw"],
                "shap_context": []
            },
            "follow_up_questions": [
                "What is this patient’s readmission risk?",
                "Where is this patient being discharged?",
                "Why is this patient high risk?"
            ],
            "limitations": [
                "This is a rule-based prototype using structured demo data."
            ]
        }

    # C. Patient Identity
    if match_any(["patient name", "what is the name", "patient id", "patient's name", "patientmrn", "mrn"]) or msg == "mrn?" or msg == "name?":
        name = identity.get("patient_name")
        mrn = identity.get("mrn")
        evidence_summary = []
        
        parts = []
        if name:
            parts.append(f"name is **{name}**")
            evidence_summary.append(f"Patient Name: {name}")
        if mrn:
            parts.append(f"MRN is **{mrn}**")
            evidence_summary.append(f"MRN: {mrn}")

        if parts:
            answer_markdown = f"This patient's " + " and ".join(parts) + f" (Patient ID: **{patient_id}**)."
        else:
            answer_markdown = "I do not have that field available for this demo patient."

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "patient_identity",
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"Patient name is {name} and MRN is {mrn}." if (name or mrn) else "Identity details are not available.",
            "evidence_summary": evidence_summary,
            "technical_evidence": {
                "structured_fields_used": ["patient_name", "mrn", "patient_id"],
                "shap_context": []
            },
            "follow_up_questions": [
                "What is this patient’s readmission risk?",
                "Where is this patient being discharged?",
                "Why is this patient high risk?"
            ],
            "limitations": [
                "This is a rule-based prototype using structured demo data."
            ]
        }

    # D. Physician or Ward
    if match_any(["doctor", "primary physician", "physician", "ward", "room number", "room nbr", "room#"]):
        physician = identity.get("primary_physician")
        ward = identity.get("ward_unit")
        room = identity.get("room_number")
        evidence_summary = []

        parts = []
        if physician:
            parts.append(f"primary physician is **{physician}**")
            evidence_summary.append(f"Primary Physician: {physician}")
        if ward:
            parts.append(f"is located in the **{ward}** ward")
            evidence_summary.append(f"Ward Unit: {ward}")
        if room:
            parts.append(f"room number **{room}**")
            evidence_summary.append(f"Room Number: {room}")

        if parts:
            answer_markdown = f"This patient's " + ", ".join(parts) + "."
        else:
            answer_markdown = "I do not have that field available for this demo patient."

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "physician_or_ward",
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"Patient is in {ward} room {room} managed by {physician}.",
            "evidence_summary": evidence_summary,
            "technical_evidence": {
                "structured_fields_used": ["primary_physician", "ward_unit", "room_number"],
                "shap_context": []
            },
            "follow_up_questions": [
                "What is the scheduled discharge time?",
                "What are the main clinical concerns?",
                "Review discharge readiness"
            ],
            "limitations": [
                "This is a rule-based prototype using structured demo data."
            ]
        }

    # E. Discharge Schedule
    if match_any(["scheduled discharge", "discharge date", "discharge time", "what time is discharge", "when is discharge", "discharge schedule"]) or ("when" in msg and "discharge" in msg):
        date = context.get("scheduled_discharge_date")
        time = context.get("scheduled_discharge_time")
        evidence_summary = []

        parts = []
        if date:
            parts.append(f"date is **{date}**")
            evidence_summary.append(f"Discharge Date: {date}")
        if time:
            parts.append(f"time is **{time}**")
            evidence_summary.append(f"Discharge Time: {time}")

        if parts:
            answer_markdown = f"This patient's scheduled discharge " + " and ".join(parts) + "."
        else:
            answer_markdown = "I do not have that field available for this demo patient."

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "discharge_schedule",
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"Discharge scheduled for {date} at {time}.",
            "evidence_summary": evidence_summary,
            "technical_evidence": {
                "structured_fields_used": ["scheduled_discharge_date", "scheduled_discharge_time"],
                "shap_context": []
            },
            "follow_up_questions": [
                "where is the patient going after discharge",
                "What are the main clinical concerns?",
                "Review discharge readiness"
            ],
            "limitations": [
                "This is a rule-based prototype using structured demo data."
            ]
        }

    # F. Discharge Destination
    if match_any(["discharge destination", "where is the patient going", "post-discharge destination", "destination after discharge", "going after discharge", "discharged to", "discharge location"]) or ("where" in msg and "discharge" in msg):
        dest = context.get("discharge_destination")
        evidence_summary = []
        if dest:
            answer_markdown = f"This patient's planned discharge destination is **{dest}**."
            evidence_summary.append(f"Discharge Destination: {dest}")
        else:
            answer_markdown = "I do not have that field available for this demo patient."

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "discharge_destination",
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"Discharge planned to {dest}.",
            "evidence_summary": evidence_summary,
            "technical_evidence": {
                "structured_fields_used": ["discharge_destination", "discharge_group"],
                "shap_context": []
            },
            "follow_up_questions": [
                "Is discharge home aligned with the risk profile?",
                "What should be reviewed before discharge?",
                "Are there follow-up concerns?"
            ],
            "limitations": [
                "This is a rule-based prototype using structured demo data."
            ]
        }

    # G. Time in Hospital
    if match_any(["length of stay", "time in hospital", "days in hospital", "days in the hospital", "stay duration", "how long"]):
        stay = context.get("time_in_hospital")
        evidence_summary = []
        if stay is not None:
            answer_markdown = f"This patient's length of stay is recorded as **{stay} days**."
            evidence_summary.append(f"Length of Stay: {stay} days")
        else:
            answer_markdown = "I do not have that field available for this demo patient."

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "time_in_hospital",
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"Length of stay is {stay} days.",
            "evidence_summary": evidence_summary,
            "technical_evidence": {
                "structured_fields_used": ["time_in_hospital"],
                "shap_context": []
            },
            "follow_up_questions": [
                "What was the admission type?",
                "What are the recorded diagnoses for this encounter?",
                "Is this patient ready for discharge?"
            ],
            "limitations": [
                "This is a rule-based prototype using structured demo data."
            ]
        }

    # H. Encounter Admission
    if match_any(["admission type", "admission source"]):
        adm_type = context.get("admission_type")
        adm_source = context.get("admission_source")
        evidence_summary = []

        parts = []
        if adm_type:
            parts.append(f"admission type was **{adm_type}**")
            evidence_summary.append(f"Admission Type: {adm_type}")
        if adm_source:
            parts.append(f"admission source was **{adm_source}**")
            evidence_summary.append(f"Admission Source: {adm_source}")

        if parts:
            answer_markdown = f"This patient's " + " and ".join(parts) + "."
        else:
            answer_markdown = "I do not have that field available for this demo patient."

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "encounter_admission",
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"Admission type {adm_type} and source {adm_source}.",
            "evidence_summary": evidence_summary,
            "technical_evidence": {
                "structured_fields_used": ["admission_type_group", "admission_source_group"],
                "shap_context": []
            },
            "follow_up_questions": [
                "how long was the patient in hospital",
                "What are the recorded diagnoses for this encounter?",
                "Is this patient ready for discharge?"
            ],
            "limitations": [
                "This is a rule-based prototype using structured demo data."
            ]
        }

    # I. Risk Category/Pct
    if (match_any(["risk category", "readmission risk", "predicted risk", "risk percentage", "probability"]) or msg == "risk?") and "why" not in msg:
        risk_cat = risk.get("risk_category")
        risk_pct = risk.get("calibrated_risk_pct")
        evidence_summary = []
        
        if risk_cat and risk_pct:
            answer_markdown = f"This patient is categorized as **{risk_cat}** with a calibrated readmission risk of **{risk_pct}%**."
            evidence_summary.extend([f"Risk Category: {risk_cat}", f"Calibrated Risk: {risk_pct}%"])
        elif risk_cat:
            answer_markdown = f"This patient is categorized as **{risk_cat}** risk."
            evidence_summary.append(f"Risk Category: {risk_cat}")
        elif risk_pct:
            answer_markdown = f"This patient has a calibrated readmission risk of **{risk_pct}%**."
            evidence_summary.append(f"Calibrated Risk: {risk_pct}%")
        else:
            answer_markdown = "I do not have that field available for this demo patient."

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "risk_category_pct",
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"Patient readmission risk is {risk_pct}% ({risk_cat}).",
            "evidence_summary": evidence_summary,
            "technical_evidence": {
                "structured_fields_used": ["risk_category", "calibrated_risk_pct", "predicted_probability_calibrated"],
                "shap_context": []
            },
            "follow_up_questions": [
                f"Why is this patient {risk_cat.lower() if risk_cat else 'high'} risk?",
                "Is the patient ready for discharge?",
                "What diagnoses were recorded for this encounter?"
            ],
            "limitations": [
                "This is a rule-based prototype using structured demo data."
            ]
        }

    # ==========================================
    # Existing Reasoning / Intent Routing
    # ==========================================

    # 1. evaluate_discharge_readiness
    discharge_terms = [
        "discharge",
        "dischurge",
        "discharg",
        "tarkhis",
        "tarkhish",
        "tarkhise",
        "tarkhishe",
        "ترخیص",
    ]
    evaluation_terms = [
        "evaluate",
        "evaluation",
        "readiness",
        "ready",
        "check",
        "review discharge",
        "review discharge plan",
        "assess",
        "assessment",
        "amade",
        "amadeye",
        "amadeh",
        "bebin",
        "hast",
        "arzyabi",
        "arzyaby",
        "arz yabi",
        "arzyaabi",
        "arziabi",
        "ارزیابی",
        "بررسی",
    ]
    possibility_terms = [
        "can we",
        "can this",
        "can the",
        "could we",
        "mitoonim",
        "mitunim",
        "mitonim",
        "mitoonam",
        "mishe",
        "mishavad",
        "میتونیم",
        "می‌تونیم",
        "می توانیم",
        "میشه",
        "آیا",
    ]
    direct_discharge_readiness = [
        "evaluate discharge",
        "discharge readiness",
        "is this patient ready for discharge",
        "review discharge plan",
        "ready for discharge",
        "discharge ready",
        "amade discharge",
        "amade dischurge",
        "amadeye discharge",
        "amadeye dischurge",
        "evaluate discharge readiness",
        "ارزیابی ترخیص",
        "آماده ترخیص",
    ]

    if (
        match_any(direct_discharge_readiness)
        or (
            match_any(discharge_terms)
            and (match_any(evaluation_terms) or match_any(possibility_terms))
        )
    ):
        res = evaluate_patient_copilot(patient_id)
        
        # Translate each phase note and compile overall report
        overall_assessment = res["overall_assessment"]
        risk_cat = overall_assessment["risk_category"]
        risk_pct = overall_assessment["calibrated_risk_pct"]
        summary = overall_assessment["summary"]
        
        key_items = res["key_review_items"]
        
        markdown_bullets = "\n".join([f"*   {item}" for item in key_items])
        answer_markdown = (
            f"### Discharge Readiness Evaluation\n\n"
            f"**Overall Assessment**: The patient is stratified as **{risk_cat} ({risk_pct}%)**.\n\n"
            f"**Clinical Summary**: {summary}\n\n"
            f"#### Key Review Items:\n{markdown_bullets}\n\n"
            f"Please review the detailed 5-phase findings in the evaluation checklist below."
        )
        
        follow_up_qs = [
            f"Why is this patient categorized as {risk_cat.lower()}?",
            "What glycemic monitoring was done for this stay?",
            "What transition support is planned post-discharge?"
        ]
        
        structured_fields = [
            "calibrated_risk_pct",
            "risk_category",
            "prior_inpatient_visits",
            "discharge_destination",
            "hba1c_tested",
            "medication_reconciliation_status"
        ]
        
        # Pull all shap contexts from phases
        all_shaps = []
        for phase in res["phases"]:
            all_shaps.extend(phase.get("shap_context", []))
        
        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "evaluate_discharge_readiness",
            "answer": "Discharge readiness evaluation completed. Please review the 5-phase structured checklist findings.",
            "evidence_used": key_items,
            "related_phases": [
                "Historical Risk Profile",
                "Current Encounter Complexity",
                "Labs & Glycemic Review",
                "Medication & Diabetes Regimen",
                "Discharge Readiness & Care Transition",
            ],
            "shap_context": all_shaps,
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"Discharge readiness evaluation completed. Patient is categorized as {risk_cat} ({risk_pct}%) with discharge planned.",
            "evidence_summary": key_items,
            "technical_evidence": {
                "shap_context": all_shaps,
                "structured_fields_used": structured_fields
            },
            "follow_up_questions": follow_up_qs,
            "limitations": [
                "This prototype uses structured demo data and precomputed SHAP outputs.",
                "It does not generate medical orders."
            ],
            "overall_assessment": overall_assessment,
            "phases": res["phases"]
        }

    # 2. why_high_risk / risk explanation
    if any(
        x in msg
        for x in [
            "why high risk",
            "why is this patient high risk",
            "risk reason",
            "readmission risk",
            "why readmission",
            "why medium risk",
            "why low risk",
            "explain risk",
            "why is it high"
        ]
    ):
        p1_risk_cat = chart["risk_prediction"]["risk_category"]
        p1_risk_pct = chart["risk_prediction"]["calibrated_risk_pct"]
        p1_inpatient = chart["box_2_clinical_snapshot"]["prior_utilization"]["prior_inpatient_visits"]
        p1_emergency = chart["box_2_clinical_snapshot"]["prior_utilization"]["prior_emergency_visits"]
        p1_util_level = chart["box_2_clinical_snapshot"]["prior_utilization"]["utilization_level"]
        p5_dest = chart["box_1_demographics_encounter"]["encounter_context"]["discharge_destination"]
        clinical_burden = chart["box_2_clinical_snapshot"]["current_admission_burden"]["clinical_burden_level"]
        total_diag = chart["box_3_clinical_review"]["diagnosis_review"]["total_diagnoses_recorded"]

        answer = (
            f"This patient is categorized as {p1_risk_cat} ({p1_risk_pct}%) mainly because of repeated prior inpatient utilization "
            f"({p1_inpatient} visits) and the model's predicted readmission risk. The available data shows {p1_inpatient} prior inpatient visits, "
            f"{p1_emergency} emergency visits, prior utilization level is {p1_util_level}, and the discharge destination is planned to {p5_dest}."
        )

        evidence = [
            f"Risk category: {p1_risk_cat}",
            f"Calibrated risk: {p1_risk_pct}%",
            f"Prior inpatient visits: {p1_inpatient}",
            f"Prior emergency visits: {p1_emergency}",
            f"Prior utilization level: {p1_util_level}",
            f"Discharge destination: {p5_dest}",
        ]

        rel_shaps = get_matching_shaps_safe(
            ["inpatient", "emergency", "outpatient", "prior_utilization", "discharge", "home", "transfer"]
        )
        translated_shaps = translate_shap_context(rel_shaps)

        markdown_shaps = "\n".join([f"*   {s}" for s in translated_shaps])
        answer_markdown = (
            f"### Readmission Risk Drivers\n\n"
            f"The patient is stratified as **{p1_risk_cat}** with a calibrated readmission risk of **{p1_risk_pct}%**.\n\n"
            f"#### Key Risk Factors:\n"
            f"*   **Prior Utilization**: The patient has **{p1_inpatient} prior inpatient visits** and **{p1_emergency} emergency visits** in the last year.\n"
            f"*   **Discharge Plan**: Planned discharge to **{p5_dest}** requires post-discharge support coordination.\n"
            f"*   **Clinical Complexity**: Rated as **{clinical_burden}** clinical burden with **{total_diag}** documented diagnoses.\n\n"
            f"#### Model Insights:\n{markdown_shaps if markdown_shaps else '*   Baseline risk factors apply.'}"
        )

        follow_up_qs = [
            "Is this patient ready for discharge?",
            "What diagnoses were recorded for this encounter?",
            "What medications is the patient on?"
        ]

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "why_high_risk",
            "answer": answer,
            "evidence_used": evidence,
            "related_phases": ["Historical Risk Profile", "Discharge Readiness & Care Transition"],
            "shap_context": rel_shaps,
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"Risk is {p1_risk_pct}% ({p1_risk_cat}) driven by {p1_inpatient} prior inpatient visits and planned discharge to {p5_dest}.",
            "evidence_summary": [
                f"Calibrated Risk: {p1_risk_pct}% ({p1_risk_cat})",
                f"Prior utilization: {p1_inpatient} inpatient, {p1_emergency} emergency visits",
                f"Discharge destination: {p5_dest}"
            ],
            "technical_evidence": {
                "shap_context": rel_shaps,
                "structured_fields_used": ["calibrated_risk_pct", "prior_inpatient_visits", "prior_emergency_visits", "discharge_destination"]
            },
            "follow_up_questions": follow_up_qs,
            "limitations": [
                "This prototype uses structured demo data and precomputed SHAP outputs.",
                "It does not generate medical orders."
            ]
        }

    # 3. labs_review
    if any(x in msg for x in ["labs", "lab result", "hba1c", "a1c", "glucose", "glycemic", "blood sugar"]):
        labs = chart["box_3_clinical_review"]["labs_glycemic_monitoring"]
        hba1c_tested = labs["hba1c_tested"]
        hba1c_res = labs["hba1c_result_status"]
        glu_tested = labs["max_glu_tested"]
        glu_res = labs["max_glucose_result_status"]
        lab_count = labs["lab_procedures_count"]

        evidence = [
            f"Lab procedures count: {lab_count}",
            f"HbA1c tested: {'Yes' if hba1c_tested else 'No'}",
            f"HbA1c result: {hba1c_res or 'Not Tested'}",
            f"Max glucose tested: {'Yes' if glu_tested else 'No'}",
            f"Max glucose result: {glu_res or 'Not Tested'}",
        ]

        if not hba1c_tested:
            answer = (
                f"The structured data shows that {lab_count} lab procedures were performed, but no HbA1c test is recorded for this encounter. "
                f"Consider ordering a follow-up glycemic check if clinically indicated. Available structured data shows no max glucose result."
            )
            recommendation = "No HbA1c test is recorded for this stay. Recommend ordering an HbA1c test or confirming recent glycemic status."
        else:
            answer = (
                f"The structured data shows {lab_count} lab procedures were performed during this encounter. "
                f"HbA1c was tested with result '{hba1c_res}' and max glucose was tested with result '{glu_res}'."
            )
            recommendation = f"HbA1c was tested with result **{hba1c_res}** (Glycemic control: {hba1c_res})."

        rel_shaps = get_matching_shaps_safe(["a1c", "glucose", "glu", "lab"])
        translated_shaps = translate_shap_context(rel_shaps)
        markdown_shaps = "\n".join([f"*   {s}" for s in translated_shaps])

        answer_markdown = (
            f"### Labs & Glycemic Monitoring Review\n\n"
            f"*   **Total Lab Procedures**: A total of **{lab_count}** lab procedures were completed.\n"
            f"*   **HbA1c Glycemic Test**: {'**Tested** (Result: ' + str(hba1c_res) + ')' if hba1c_tested else 'Not Tested'}\n"
            f"*   **Max Glucose Recorded**: {'**Tested** (Result: ' + str(glu_res) + ')' if glu_tested else 'Not Tested'}\n\n"
            f"#### Recommendation:\n*   {recommendation}\n\n"
            f"#### Model Insights:\n{markdown_shaps if markdown_shaps else '*   Glycemic indicators fall within default weights.'}"
        )

        follow_up_qs = [
            "What diabetes medications is the patient on?",
            "Is the patient ready for discharge?",
            "Why is this patient high risk?"
        ]

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "labs_review",
            "answer": answer,
            "evidence_used": evidence,
            "related_phases": ["Labs & Glycemic Review"],
            "shap_context": rel_shaps,
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"HbA1c test is {hba1c_res or 'not recorded'} during this encounter with {lab_count} lab procedures performed.",
            "evidence_summary": [
                f"Lab count: {lab_count}",
                f"HbA1c tested: {'Yes (' + str(hba1c_res) + ')' if hba1c_tested else 'No'}",
                f"Max Glucose: {glu_res or 'Not Tested'}"
            ],
            "technical_evidence": {
                "shap_context": rel_shaps,
                "structured_fields_used": ["lab_procedures_count", "hba1c_tested", "hba1c_result_status", "max_glu_tested", "max_glucose_result_status"]
            },
            "follow_up_questions": follow_up_qs,
            "limitations": [
                "This prototype uses structured demo data and precomputed SHAP outputs.",
                "It does not generate medical orders."
            ]
        }

    # 4. medication_review
    if any(
        x in msg
        for x in [
            "medication",
            "meds",
            "medicine",
            "insulin",
            "metformin",
            "pharmacy",
            "reconciliation",
            "diabetes education",
        ]
    ):
        meds = chart["box_3_clinical_review"]["medication_review"]
        med_count = meds["active_medication_count"]
        diab_med = meds["diabetes_medication_used"]
        insulin = meds["insulin_status"]
        change = meds["medication_change_during_stay"]
        key_meds = meds["key_diabetes_medications"]
        recon = meds["medication_reconciliation_status"]
        pharm = meds["reviewed_by_pharmacist"]
        edu_status = meds.get("diabetes_education_status", "Unknown")

        evidence = [
            f"Active medication count: {med_count}",
            f"Diabetes meds used: {diab_med}",
            f"Insulin status: {insulin}",
            f"Medication change during stay: {change}",
            f"Key diabetes medications: {key_meds or 'None'}",
            f"Medication reconciliation status: {recon or 'Unknown'}",
            f"Reviewed by pharmacist: {pharm or 'No'}",
        ]

        answer = (
            f"The medication profile shows {med_count} active medications. Diabetes medications are indicated as '{diab_med}' "
            f"with insulin status '{insulin}' and medication change status '{change}'. "
            f"Medication reconciliation status is currently '{recon}' and pharmacist review is conducted by {pharm or 'Not Assigned'}."
        )

        rel_shaps = get_matching_shaps_safe(["medication", "insulin", "metformin", "diabetesmed", "change"])
        translated_shaps = translate_shap_context(rel_shaps)
        markdown_shaps = "\n".join([f"*   {s}" for s in translated_shaps])

        answer_markdown = (
            f"### Medication & Regimen Review\n\n"
            f"Review of the active inpatient medication profile:\n\n"
            f"*   **Active Medication Count**: **{med_count}** medications on file.\n"
            f"*   **Diabetes Medications**: **{key_meds or 'None recorded'}** (Active: {diab_med}).\n"
            f"*   **Insulin Regimen**: Patient is **{insulin}**.\n"
            f"*   **Inpatient Adjustments**: Regimen adjustments were: **{change}**.\n\n"
            f"#### Safety & Reconciliation:\n"
            f"*   **Medication Reconciliation**: status is **{recon}**.\n"
            f"*   **Pharmacist Review**: Clinical pharmacist review is **{pharm}**.\n"
            f"*   **Diabetes Education**: **{edu_status}**.\n\n"
            f"#### Model Insights:\n{markdown_shaps if markdown_shaps else '*   Medication factors are within standard risk profiles.'}"
        )

        follow_up_qs = [
            "Is diabetes education completed?",
            "What glycemic labs were recorded?",
            "Is the patient ready for discharge?"
        ]

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "medication_review",
            "answer": answer,
            "evidence_used": evidence,
            "related_phases": ["Medication & Diabetes Regimen"],
            "shap_context": rel_shaps,
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"Active medication count is {med_count}. Medication reconciliation is {recon} with pharmacist review: {pharm}.",
            "evidence_summary": [
                f"Total active meds: {med_count}",
                f"Insulin status: {insulin}",
                f"Reconciliation: {recon}",
                f"Pharmacist review: {pharm}"
            ],
            "technical_evidence": {
                "shap_context": rel_shaps,
                "structured_fields_used": ["active_medication_count", "diabetes_medication_used", "insulin_status", "medication_change_during_stay", "key_diabetes_medications", "medication_reconciliation_status", "reviewed_by_pharmacist"]
            },
            "follow_up_questions": follow_up_qs,
            "limitations": [
                "This prototype uses structured demo data and precomputed SHAP outputs.",
                "It does not generate medical orders."
            ]
        }

    # 5. diagnosis_summary
    if any(x in msg for x in ["diagnosis", "diagnoses", "condition", "clinical complexity", "what conditions"]):
        diag = chart["box_3_clinical_review"]["diagnosis_review"]
        diag_1 = diag["primary_diagnosis"]
        diag_2 = diag["secondary_diagnosis"]
        diag_3 = diag["third_diagnosis"]
        total_diag = diag["total_diagnoses_recorded"]
        clinical_burden = chart["box_2_clinical_snapshot"]["current_admission_burden"]["clinical_burden_level"]

        evidence = [
            f"Primary diagnosis: {diag_1}",
            f"Secondary diagnosis: {diag_2}",
            f"Third diagnosis: {diag_3}",
            f"Total diagnoses recorded: {total_diag}",
            f"Clinical burden level: {clinical_burden}",
        ]

        answer = (
            f"The clinical complexity assessment shows a total of {total_diag} diagnoses recorded. "
            f"The primary diagnosis is '{diag_1}', followed by '{diag_2}' and '{diag_3}'. "
            f"The clinical burden level is categorized as {clinical_burden}."
        )
        if total_diag > 3:
            answer += " Note: Only the top 3 structured diagnosis groups are available in this demo dataset."

        rel_shaps = get_matching_shaps_safe(["diagnoses", "diag"])
        translated_shaps = translate_shap_context(rel_shaps)
        markdown_shaps = "\n".join([f"*   {s}" for s in translated_shaps])

        answer_markdown = (
            f"### Diagnosis & Encounter Complexity\n\n"
            f"Clinical complexity summary based on recorded diagnoses:\n\n"
            f"*   **Total Documented Diagnoses**: **{total_diag}** diagnoses.\n"
            f"*   **Clinical Burden Classification**: Rated as **{clinical_burden}** clinical burden.\n"
            f"*   **Top 3 Recorded Diagnosis Groups**:\n"
            f"    1.  **Primary**: {diag_1}\n"
            f"    2.  **Secondary**: {diag_2}\n"
            f"    3.  **Tertiary**: {diag_3}\n\n"
            f"*Note: Only the top 3 structured diagnosis groups are available in this demo.*\n\n"
            f"#### Model Insights:\n{markdown_shaps if markdown_shaps else '*   Diagnosis metrics are within normal baseline weights.'}"
        )

        follow_up_qs = [
            "Why is this patient high risk?",
            "What medications is the patient on?",
            "Is the patient ready for discharge?"
        ]

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "diagnosis_summary",
            "answer": answer,
            "evidence_used": evidence,
            "related_phases": ["Current Encounter Complexity"],
            "shap_context": rel_shaps,
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"Primary diagnosis is {diag_1} with {total_diag} total diagnoses and {clinical_burden} clinical burden level.",
            "evidence_summary": [
                f"Primary: {diag_1}",
                f"Clinical burden: {clinical_burden}",
                f"Total diagnoses: {total_diag}"
            ],
            "technical_evidence": {
                "shap_context": rel_shaps,
                "structured_fields_used": ["primary_diagnosis", "secondary_diagnosis", "third_diagnosis", "total_diagnoses_recorded", "clinical_burden_level"]
            },
            "follow_up_questions": follow_up_qs,
            "limitations": [
                "This prototype uses structured demo data and precomputed SHAP outputs.",
                "It does not generate medical orders."
            ]
        }

    # 6. follow_up_review
    if any(
        x in msg
        for x in [
            "follow up",
            "follow-up",
            "after discharge",
            "home support",
            "care transition",
            "support plan",
        ]
    ):
        risk_cat = chart["risk_prediction"]["risk_category"]
        dest = chart["box_1_demographics_encounter"]["encounter_context"]["discharge_destination"]
        transition_note = chart["synthetic_context"]["care_transition_note"]
        social_note = chart["synthetic_context"]["social_context_note"]
        planner = chart["box_1_demographics_encounter"]["encounter_context"]["discharge_planner"]

        evidence = [
            f"Risk category: {risk_cat}",
            f"Discharge destination: {dest}",
            f"Discharge planner: {planner or 'Not Assigned'}",
            f"Care transition note: {transition_note or 'None'}",
            f"Social context note: {social_note or 'None'}",
        ]

        answer = (
            f"The care transition review identifies this patient as {risk_cat} with discharge planned to '{dest}'. "
            f"Discharge planner {planner or 'Not Assigned'} has documented the transition note: '{transition_note}'. "
            f"Social context note suggests: '{social_note}'."
        )

        rel_shaps = get_matching_shaps_safe(["discharge", "home", "transfer", "snf", "nursing"])
        translated_shaps = translate_shap_context(rel_shaps)
        markdown_shaps = "\n".join([f"*   {s}" for s in translated_shaps])

        answer_markdown = (
            f"### Care Transition & Discharge Planning\n\n"
            f"Current transition details for this encounter:\n\n"
            f"*   **Discharge Destination**: Planned for **{dest}**.\n"
            f"*   **Discharge Planner**: Managed by **{planner or 'Not Assigned'}**.\n"
            f"*   **Care Transition Notes**: \"{transition_note or 'No notes recorded.'}\"\n"
            f"*   **Social Context**: \"{social_note or 'No social constraints documented.'}\"\n\n"
            f"#### Model Insights:\n{markdown_shaps if markdown_shaps else '*   Standard care transition weights apply.'}"
        )

        follow_up_qs = [
            "Is the patient ready for discharge?",
            "Why is this patient high risk?",
            "What glycemic or HbA1c labs were recorded?"
        ]

        return {
            "patient_id": patient_id,
            "mode": "rule_based_chat_prototype",
            "intent": "follow_up_review",
            "answer": answer,
            "evidence_used": evidence,
            "related_phases": ["Discharge Readiness & Care Transition"],
            "shap_context": rel_shaps,
            "answer_markdown": answer_markdown,
            "plain_language_summary": f"Discharge destination is {dest}. Transition planner is {planner}. Care note: '{transition_note}'.",
            "evidence_summary": [
                f"Destination: {dest}",
                f"Planner: {planner or 'None'}",
                f"Transition note: {transition_note or 'None'}"
            ],
            "technical_evidence": {
                "shap_context": rel_shaps,
                "structured_fields_used": ["discharge_destination", "discharge_planner", "care_transition_note", "social_context_note"]
            },
            "follow_up_questions": follow_up_qs,
            "limitations": [
                "This prototype uses structured demo data and precomputed SHAP outputs.",
                "It does not generate medical orders."
            ]
        }

    # 7. unsupported
    follow_up_qs = [
        "Why is this patient high risk?",
        "Evaluate discharge readiness",
        "What labs were done for this patient?"
    ]
    
    answer_markdown = (
        f"### Interactive Clinical Assistant\n\n"
        f"I can help you review patient clinical details and evaluate readmission risk. Try asking:\n\n"
        f"*   *Why is this patient high risk?*\n"
        f"*   *Evaluate discharge readiness*\n"
        f"*   *What labs were done for this patient?*\n"
        f"*   *Review this patient's medications*\n"
        f"*   *What are the patient's diagnoses?*\n"
        f"*   *What follow-up support is planned?*"
    )
    
    return {
        "patient_id": patient_id,
        "mode": "rule_based_chat_prototype",
        "intent": "unsupported",
        "answer": (
            "I can currently help with discharge readiness, readmission risk reasons, labs, medications, diagnoses, and follow-up planning. "
            "This is a rule-based prototype, so free-form clinical reasoning will be added in a later RAG/LLM phase."
        ),
        "evidence_used": [],
        "related_phases": [],
        "shap_context": [],
        "answer_markdown": answer_markdown,
        "plain_language_summary": "I can help with discharge readiness, readmission risk reasons, labs, medications, diagnoses, and follow-up planning.",
        "evidence_summary": [],
        "technical_evidence": {
            "shap_context": [],
            "structured_fields_used": []
        },
        "follow_up_questions": follow_up_qs,
        "limitations": [
            "This prototype uses structured demo data and precomputed SHAP outputs.",
            "It does not generate medical orders."
        ]
    }
