from __future__ import annotations

import shutil

from fastapi.testclient import TestClient

from app.database import get_db_path
from app.main import app

client = TestClient(app)


def _first_patient_id() -> str:
    return client.get("/api/patients?limit=1").json()["items"][0]["patient_id"]


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_db_health():
    response = client.get("/api/db/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["table_counts"]["patient_queue"] == 100


def test_patient_queue_default_and_filters():
    response = client.get("/api/patients")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 100
    first_item = body["items"][0]
    assert first_item["calibrated_risk_pct"] == 34.63
    assert first_item["age_band"] == "[80-90)"
    assert isinstance(first_item["display_age"], int)
    assert 80 <= first_item["display_age"] <= 89
    assert first_item["admission_source_raw"] == "Referral"
    assert first_item["admission_source"] == "Referral"

    emergency = client.get("/api/patients?search=DEMO-002")
    assert emergency.status_code == 200
    emergency_item = emergency.json()["items"][0]
    assert emergency_item["admission_source_raw"] == "Emergency_Room"
    assert emergency_item["admission_source"] == "Emergency Room"

    high_risk = client.get("/api/patients?risk_category=High%20Risk")
    assert high_risk.status_code == 200
    assert high_risk.json()["total"] == 40

    paged = client.get("/api/patients?limit=10&offset=0")
    assert paged.status_code == 200
    assert len(paged.json()["items"]) == 10


def test_patient_detail_contract_and_related_endpoints():
    patient_id = _first_patient_id()
    detail = client.get(f"/api/patients/{patient_id}")
    assert detail.status_code == 200
    body = detail.json()
    for key in [
        "box_1_demographics_encounter",
        "box_2_clinical_snapshot",
        "box_3_clinical_review",
        "risk_prediction",
        "shap_top3",
        "interventions",
    ]:
        assert key in body
    assert "recommended_action" not in body.get("synthetic_context", {})
    demographics = body["box_1_demographics_encounter"]["demographics"]
    assert isinstance(demographics["display_age"], int)
    assert demographics["age_band"].startswith("[")
    assert body["box_3_clinical_review"]["diagnosis_review"]["diagnosis_limitation_note"]

    for path in [
        f"/api/patients/{patient_id}/risk",
        f"/api/patients/{patient_id}/shap/top3",
        f"/api/patients/{patient_id}/shap/all",
        f"/api/patients/{patient_id}/clinical-review",
        f"/api/patients/{patient_id}/interventions",
    ]:
        response = client.get(path)
        assert response.status_code == 200


def test_legacy_recommended_interventions_hidden_from_user_endpoint():
    patient_id = _first_patient_id()
    response = client.get(f"/api/patients/{patient_id}/interventions")
    assert response.status_code == 200
    assert response.json() == []


def test_invalid_patient():
    response = client.get("/api/patients/DOES-NOT-EXIST")
    assert response.status_code == 404


def test_intervention_write_flow_uses_temp_database(monkeypatch, tmp_path):
    test_db = tmp_path / "diabetes_readmission_demo.sqlite"
    shutil.copy2(get_db_path(), test_db)
    monkeypatch.setenv("DIABETES_READMISSION_DB", str(test_db))

    patient_id = _first_patient_id()
    created = client.post(
        f"/api/patients/{patient_id}/interventions",
        json={
            "intervention_type": "Medication review",
            "intervention_status": "planned",
            "created_by": "Pytest",
            "notes": "Temporary test intervention.",
        },
    )
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["intervention_status"] == "planned"
    assert created_body["source_type"] == "user_saved"
    assert created_body["is_user_created"] is True
    assert created_body["is_editable"] is True

    listed = client.get(f"/api/patients/{patient_id}/interventions")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    patched = client.patch(
        f"/api/interventions/{created_body['intervention_id']}",
        json={"intervention_status": "completed"},
    )
    assert patched.status_code == 200
    assert patched.json()["intervention_status"] == "completed"


def test_invalid_intervention_inputs_rejected(monkeypatch, tmp_path):
    test_db = tmp_path / "diabetes_readmission_demo.sqlite"
    shutil.copy2(get_db_path(), test_db)
    monkeypatch.setenv("DIABETES_READMISSION_DB", str(test_db))
    patient_id = _first_patient_id()

    invalid_status = client.post(
        f"/api/patients/{patient_id}/interventions",
        json={"intervention_type": "Medication review", "intervention_status": "Recommended"},
    )
    assert invalid_status.status_code == 422

    invalid_type = client.post(
        f"/api/patients/{patient_id}/interventions",
        json={"intervention_type": "Static recommendation", "intervention_status": "planned"},
    )
    assert invalid_type.status_code == 422


def test_summary():
    response = client.get("/api/summary")
    assert response.status_code == 200
    assert response.json()["total_demo_patients"] == 100


def test_copilot_evaluate():
    patient_id = _first_patient_id()
    response = client.get(f"/api/patients/{patient_id}/copilot/evaluate")
    assert response.status_code == 200
    body = response.json()
    assert body["patient_id"] == patient_id
    assert body["mode"] == "rule_based_prototype"
    assert "overall_assessment" in body
    assert "phases" in body
    assert len(body["phases"]) == 5
    assert "key_review_items" in body
    assert "data_limitations" in body


def test_copilot_chat():
    patient_id = _first_patient_id()
    # 1. evaluate_discharge_readiness
    res1 = client.post(f"/api/patients/{patient_id}/copilot/chat", json={"message": "Evaluate discharge readiness"})
    assert res1.status_code == 200
    body1 = res1.json()
    assert body1["intent"] == "evaluate_discharge_readiness"
    assert body1["overall_assessment"] is not None
    assert len(body1["phases"]) == 5
    assert body1["answer_markdown"] is not None
    assert len(body1["follow_up_questions"]) == 3

    # 2. why_high_risk
    res2 = client.post(f"/api/patients/{patient_id}/copilot/chat", json={"message": "Why is this patient high risk?"})
    assert res2.status_code == 200
    body2 = res2.json()
    assert body2["intent"] == "why_high_risk"
    assert "risk category" in "".join(body2["evidence_used"]).lower()
    assert body2["answer_markdown"] is not None
    assert body2["plain_language_summary"] is not None
    assert len(body2["follow_up_questions"]) == 3
    assert "shap_context" in body2["technical_evidence"]
    assert "structured_fields_used" in body2["technical_evidence"]
    assert len(body2["evidence_summary"]) > 0

    # 3. labs_review
    res3 = client.post(f"/api/patients/{patient_id}/copilot/chat", json={"message": "Review labs"})
    assert res3.status_code == 200
    body3 = res3.json()
    assert body3["intent"] == "labs_review"
    assert body3["answer_markdown"] is not None
    assert len(body3["follow_up_questions"]) == 3

    # 4. medication_review
    res4 = client.post(f"/api/patients/{patient_id}/copilot/chat", json={"message": "Review medications"})
    assert res4.status_code == 200
    body4 = res4.json()
    assert body4["intent"] == "medication_review"
    assert body4["answer_markdown"] is not None
    assert len(body4["follow_up_questions"]) == 3

    # 5. diagnosis_summary
    res5 = client.post(f"/api/patients/{patient_id}/copilot/chat", json={"message": "Summarize diagnoses"})
    assert res5.status_code == 200
    body5 = res5.json()
    assert body5["intent"] == "diagnosis_summary"
    assert body5["answer_markdown"] is not None
    assert len(body5["follow_up_questions"]) == 3

    # 6. follow_up_review
    res6 = client.post(f"/api/patients/{patient_id}/copilot/chat", json={"message": "Review follow-up needs"})
    assert res6.status_code == 200
    body6 = res6.json()
    assert body6["intent"] == "follow_up_review"
    assert body6["answer_markdown"] is not None
    assert len(body6["follow_up_questions"]) == 3

    # 7. unsupported
    res7 = client.post(f"/api/patients/{patient_id}/copilot/chat", json={"message": "What is the weather?"})
    assert res7.status_code == 200
    body7 = res7.json()
    assert body7["intent"] == "unsupported"
    assert body7["answer_markdown"] is not None
    assert len(body7["follow_up_questions"]) == 3


def test_copilot_chat_basic_facts():
    patient_id = _first_patient_id()

    # 1. Age
    res = client.post(f"/api/patients/{patient_id}/copilot/chat", json={"message": "how old is this patient"})
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "patient_age"
    assert "years old" in body["answer_markdown"]
    assert len(body["follow_up_questions"]) == 3

    # 2. Gender
    res = client.post(f"/api/patients/{patient_id}/copilot/chat", json={"message": "what is the patient gender"})
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "patient_gender"
    assert "gender is recorded" in body["answer_markdown"]
    assert len(body["follow_up_questions"]) == 3

    # 3. Discharge Destination
    res = client.post(f"/api/patients/{patient_id}/copilot/chat", json={"message": "where is this patient being discharged"})
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "discharge_destination"
    assert "planned discharge destination" in body["answer_markdown"]
    assert len(body["follow_up_questions"]) == 3

    # 4. Risk Category / Pct
    res = client.post(f"/api/patients/{patient_id}/copilot/chat", json={"message": "what is the readmission risk"})
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "risk_category_pct"
    assert "risk" in body["answer_markdown"].lower()
    assert len(body["follow_up_questions"]) == 3

    # 5. Physician / Doctor
    res = client.post(f"/api/patients/{patient_id}/copilot/chat", json={"message": "who is the primary physician"})
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "physician_or_ward"
    assert "primary physician" in body["answer_markdown"].lower()
    assert len(body["follow_up_questions"]) == 3


def test_copilot_ask():
    patient_id = _first_patient_id()
    # Test a simple factual question
    res = client.post(
        f"/api/patients/{patient_id}/copilot/ask",
        json={"message": "how old is this patient?", "conversation_history": []}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["patient_id"] == patient_id
    assert body["mode"] == "gemini_patient_chat"
    assert "answer_markdown" in body
    assert len(body["follow_up_questions"]) == 3
    assert "context_used" in body
    assert "structured_patient_data" in body["context_used"]
    assert "safety_note" in body





