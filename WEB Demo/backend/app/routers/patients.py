from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas import PatientQueueResponse, CopilotChatRequest, CopilotChatResponse, CopilotAskRequest, CopilotAskResponse
from app.services.patient_service import get_patient_chart, list_patients

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=PatientQueueResponse)
def patient_queue(
    risk_category: str | None = None,
    gender: str | None = None,
    primary_diagnosis_group: str | None = None,
    admission_source: str | None = None,
    discharge_destination: str | None = None,
    min_risk: float | None = None,
    max_risk: float | None = None,
    search: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    min_time_in_hospital: int | None = None,
    max_time_in_hospital: int | None = None,
    duplicate_first_name: bool | None = None,
    first_name: str | None = None,
    race: str | None = None,
    primary_physician: str | None = None,
    ward_unit: str | None = None,
    room_number: str | None = None,
    has_lab_report: bool | None = None,
    lab_report_type: str | None = None,
    lab_report_status: str | None = None,
    lab_report_source_basis: str | None = None,
    sort_by: str | None = "calibrated_risk_pct",
    sort_order: str | None = "desc",
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return list_patients(locals())


@router.get("/{patient_id}")
def patient_chart(patient_id: str) -> dict:
    return get_patient_chart(patient_id)


@router.get("/{patient_id}/copilot/evaluate")
def evaluate_patient_discharge(patient_id: str) -> dict:
    from app.services.copilot_service import evaluate_patient_copilot
    return evaluate_patient_copilot(patient_id)


@router.post("/{patient_id}/copilot/chat", response_model=CopilotChatResponse)
def chat_patient_discharge(patient_id: str, payload: CopilotChatRequest) -> dict:
    from app.services.copilot_service import chat_patient_copilot
    return chat_patient_copilot(patient_id, payload.message)


@router.post("/{patient_id}/copilot/ask", response_model=CopilotAskResponse)
async def ask_patient_copilot_gemini(patient_id: str, payload: CopilotAskRequest) -> dict:
    from app.services.gemini_copilot_service import ask_copilot_gemini
    history = [msg.model_dump() for msg in payload.conversation_history]
    return await ask_copilot_gemini(patient_id, payload.message, history)
