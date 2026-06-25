from __future__ import annotations

import os
import json
from typing import Any
from app.services.patient_service import get_patient_chart
from app.database import fetch_all

def get_lab_report_for_patient(patient_id: str) -> dict | None:
    base_dir = os.getcwd()
    lab_report_path = os.path.join(base_dir, "lab_report_package_for_codex", "lab_reports_all.json")
    if not os.path.exists(lab_report_path):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        lab_report_path = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "lab_report_package_for_codex", "lab_reports_all.json"))
        
    if os.path.exists(lab_report_path):
        try:
            with open(lab_report_path, "r") as f:
                reports = json.load(f)
                for r in reports:
                    if r.get("metadata", {}).get("patient_id") == patient_id:
                        return r
        except Exception:
            pass
    return None

def build_patient_copilot_context(patient_id: str) -> dict[str, Any]:
    chart = get_patient_chart(patient_id)
    encounter_id = chart["encounter_id"]
    
    # 1. Fetch all SHAP features
    shap_rows = fetch_all(
        "SELECT feature, feature_label, feature_value, shap_value, effect_direction FROM shap_all_features WHERE encounter_id = ?",
        [encounter_id],
    )
    shap_list = [dict(r) for r in shap_rows]
    
    # 2. Fetch lab report
    lab_report = get_lab_report_for_patient(patient_id)
    
    return {
        "chart": chart,
        "shap_all": shap_list,
        "lab_report": lab_report
    }

def serialize_context_to_text(context: dict[str, Any]) -> str:
    chart = context["chart"]
    shap_all = context["shap_all"]
    lab_report = context["lab_report"]
    
    demo_enc = chart.get("box_1_demographics_encounter", {})
    identity = demo_enc.get("patient_identity", {})
    demo = demo_enc.get("demographics", {})
    enc = demo_enc.get("encounter_context", {})
    
    snapshot = chart.get("box_2_clinical_snapshot", {})
    util = snapshot.get("prior_utilization", {})
    burden = snapshot.get("current_admission_burden", {})
    
    reviews = chart.get("box_3_clinical_review", {})
    labs_mon = reviews.get("labs_glycemic_monitoring", {})
    med_rev = reviews.get("medication_review", {})
    diag_rev = reviews.get("diagnosis_review", {})
    
    risk = chart.get("risk_prediction", {})
    shap_top3 = chart.get("shap_top3", [])
    
    lines = []
    lines.append("=== PATIENT CLINICAL CONTEXT ===")
    lines.append(f"Patient ID: {chart.get('patient_id')}")
    lines.append(f"Patient Name: {identity.get('patient_name')}")
    lines.append(f"MRN: {identity.get('mrn')}")
    lines.append(f"Age: {demo.get('display_age')} years old (Age Band: {demo.get('age_band')}, Midpoint: {demo.get('age_numeric')})")
    lines.append(f"Gender: {demo.get('gender')}")
    lines.append(f"Race: {demo.get('race')}")
    
    lines.append("\n=== ENCOUNTER CONTEXT ===")
    lines.append(f"Primary Physician: {identity.get('primary_physician')}")
    lines.append(f"Location: Ward {identity.get('ward_unit')}, Room {identity.get('room_number')}")
    lines.append(f"Admission Type: {enc.get('admission_type')}")
    lines.append(f"Admission Source: {enc.get('admission_source')}")
    lines.append(f"Length of Stay: {enc.get('time_in_hospital')} days")
    lines.append(f"Scheduled Discharge: {enc.get('scheduled_discharge_date')} at {enc.get('scheduled_discharge_time')}")
    lines.append(f"Discharge Planner: {enc.get('discharge_planner')}")
    lines.append(f"Discharge Destination: {enc.get('discharge_destination')}")
    
    lines.append("\n=== PRIOR HEALTHCARE UTILIZATION (PAST YEAR) ===")
    lines.append(f"Prior Inpatient Visits: {util.get('prior_inpatient_visits')}")
    lines.append(f"Prior Emergency Visits: {util.get('prior_emergency_visits')}")
    lines.append(f"Prior Outpatient Visits: {util.get('prior_outpatient_visits')}")
    lines.append(f"Total Prior Visits: {util.get('total_prior_utilization')}")
    lines.append(f"Utilization Level Rating: {util.get('utilization_level')}")
    
    lines.append("\n=== CURRENT ENCOUNTER COMPLEXITY ===")
    lines.append(f"Diagnoses Recorded: {burden.get('diagnoses_recorded')}")
    lines.append(f"Active Medications: {burden.get('active_medications')}")
    lines.append(f"Lab Procedures Performed: {burden.get('lab_procedures')}")
    lines.append(f"Non-lab Procedures: {burden.get('procedures')}")
    lines.append(f"Clinical Complexity Burden Level: {burden.get('clinical_burden_level')}")
    
    lines.append("\n=== LABS & GLYCEMIC REVIEW ===")
    lines.append(f"HbA1c Result Status: {labs_mon.get('hba1c_result_status')}")
    lines.append(f"HbA1c Tested: {'Yes' if labs_mon.get('hba1c_tested') == 1 else 'No'}")
    lines.append(f"Max Glucose Serum Result Status: {labs_mon.get('max_glucose_result_status')}")
    lines.append(f"Max Glucose Tested: {'Yes' if labs_mon.get('max_glu_tested') == 1 else 'No'}")
    lines.append(f"Last Lab Review Date/Time: {labs_mon.get('last_lab_review_timestamp')}")
    lines.append(f"Reviewed By: {labs_mon.get('reviewed_by')}")
    if lab_report:
        lines.append("Structured Lab Report Found:")
        lines.append(f"  - Test: {lab_report.get('result', {}).get('test_name')}")
        lines.append(f"  - Result Value: {lab_report.get('result', {}).get('simulated_numeric_result')} {lab_report.get('result', {}).get('unit')}")
        lines.append(f"  - Status: {lab_report.get('result', {}).get('status_label')}")
        lines.append(f"  - Interpretation: {lab_report.get('interpretation')}")
        
    lines.append("\n=== MEDICATION & DIABETES REGIMEN ===")
    lines.append(f"Diabetes Medication Active: {med_rev.get('diabetes_medication_used')}")
    lines.append(f"Insulin Therapy Status: {med_rev.get('insulin_status')}")
    lines.append(f"Medication Change During Stay: {med_rev.get('medication_change_during_stay')}")
    lines.append(f"Active Medications Count: {med_rev.get('active_medication_count')}")
    lines.append(f"Key Diabetes Medications: {med_rev.get('key_diabetes_medications')}")
    lines.append(f"Medication Reconciliation Status: {med_rev.get('medication_reconciliation_status')}")
    lines.append(f"Diabetes Education Status: {med_rev.get('diabetes_education_status')}")
    lines.append(f"Reviewed by Pharmacist: {med_rev.get('reviewed_by_pharmacist')}")
    
    lines.append("\n=== DIAGNOSES RECORDED ===")
    lines.append(f"Primary Diagnosis: {diag_rev.get('primary_diagnosis')}")
    lines.append(f"Secondary Diagnosis: {diag_rev.get('secondary_diagnosis')}")
    lines.append(f"Tertiary Diagnosis: {diag_rev.get('third_diagnosis')}")
    lines.append(f"Total Diagnoses: {diag_rev.get('total_diagnoses_recorded')}")
    if diag_rev.get("diagnosis_timeline"):
        lines.append("Diagnosis Timeline & Notes:")
        for t in diag_rev["diagnosis_timeline"]:
            lines.append(f"  - [{t.get('date_recorded')}] Rank {t.get('diagnosis_rank')}: {t.get('diagnosis_label')} ({t.get('diagnosis_group')}) by {t.get('diagnosed_by')} ({t.get('department_specialty')}). Note: {t.get('clinical_note')}")
            
    lines.append("\n=== SYNTHETIC CONTEXT NOTES ===")
    synth = chart.get("synthetic_context", {})
    lines.append(f"Clinical Summary: {synth.get('clinical_summary_note')}")
    lines.append(f"Social Context: {synth.get('social_context_note')}")
    lines.append(f"Care Transition Planning: {synth.get('care_transition_note')}")
    
    lines.append("\n=== READMISSION RISK MODEL PREDICTIONS ===")
    lines.append(f"ML Model Risk Category: {risk.get('risk_category')}")
    lines.append(f"Model Predicted Probability: {risk.get('predicted_probability_calibrated')}")
    lines.append(f"Model Calibrated Risk %: {risk.get('calibrated_risk_pct')}%")
    lines.append(f"Model Predicted Class (1=Readmitted, 0=Stable): {risk.get('predicted_class')}")
    lines.append(f"Actual 30d Readmission Outcome (Ground Truth): {risk.get('actual_readmitted_30d')}")
    
    lines.append("\n=== ML MODEL RISK ATTRIBUTION DRIVERS (SHAP VALUES) ===")
    lines.append("Note: SHAP values represent mathematical feature weights explaining the machine learning prediction score. They are evidence of what the model weighted, NOT clinical causality of readmission.")
    lines.append("Top 3 Risk Drivers:")
    for d in shap_top3:
        lines.append(f"  - Rank {d.get('rank')}: {d.get('feature_label')} ({d.get('feature')}) = {d.get('feature_value')} has SHAP value {d.get('shap_value')} ({d.get('effect_direction')})")
        
    lines.append("\nAll SHAP feature attributions:")
    for r in shap_all:
        lines.append(f"  - Feature: {r.get('feature_label') or r.get('feature')} ({r.get('feature')}) = {r.get('feature_value')} has SHAP {r.get('shap_value')}")
        
    return "\n".join(lines)
