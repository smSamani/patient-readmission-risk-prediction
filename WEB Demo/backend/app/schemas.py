from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AllowedInterventionType = Literal[
    "7-day follow-up call",
    "Medication review",
    "Community nurse referral",
    "HbA1c test before discharge",
    "Diabetes education",
    "Discharge destination review",
    "Primary care appointment",
    "Other",
]
AllowedInterventionStatus = Literal["planned", "in_progress", "completed", "cancelled"]


class PatientQueueItem(BaseModel):
    patient_id: str
    encounter_id: int
    model_row_id: int
    patient_name: str
    age: str
    age_band: str | None = None
    display_age: int | None = None
    gender: str
    gender_raw: str | None = None
    primary_diagnosis_group: str | None = None
    primary_diagnosis_group_raw: str | None = None
    admission_source: str | None = None
    admission_source_raw: str | None = None
    discharge_destination: str | None = None
    discharge_destination_raw: str | None = None
    calibrated_risk_pct: float | None = None
    risk_category: str | None = None
    risk_category_raw: str | None = None
    view_digital_chart_url: str


class PatientQueueResponse(BaseModel):
    items: list[PatientQueueItem]
    total: int
    limit: int
    offset: int


class InterventionCreate(BaseModel):
    intervention_type: AllowedInterventionType
    intervention_status: AllowedInterventionStatus = "planned"
    created_by: str = Field(default="Discharge Planner", min_length=1, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class InterventionUpdate(BaseModel):
    intervention_status: AllowedInterventionStatus | None = None
    notes: str | None = Field(default=None, max_length=1000)
    created_by: str | None = Field(default=None, min_length=1, max_length=120)


class CopilotChatRequest(BaseModel):
    message: str


class TechnicalEvidence(BaseModel):
    shap_context: list[str] = Field(default_factory=list)
    structured_fields_used: list[str] = Field(default_factory=list)


class CopilotChatResponse(BaseModel):
    patient_id: str
    mode: str
    intent: str
    answer: str | None = None
    evidence_used: list[str] | None = None
    related_phases: list[str] | None = None
    shap_context: list[str] | None = None
    answer_markdown: str | None = None
    plain_language_summary: str | None = None
    evidence_summary: list[str] | None = None
    technical_evidence: TechnicalEvidence | None = None
    follow_up_questions: list[str] | None = None
    limitations: list[str] | None = None
    overall_assessment: dict[str, Any] | None = None
    phases: list[dict[str, Any]] | None = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CopilotAskRequest(BaseModel):
    message: str
    conversation_history: list[ChatMessage] = Field(default_factory=list)


class CopilotContextUsed(BaseModel):
    structured_patient_data: bool = True
    risk_prediction: bool = True
    shap_summary: bool = True
    clinical_reviews: bool = True
    diagnosis_timeline: bool = True
    lab_reports: bool = True


class CopilotAskResponse(BaseModel):
    patient_id: str
    mode: str = "gemini_patient_chat"
    answer_markdown: str
    follow_up_questions: list[str]
    context_used: CopilotContextUsed
    safety_note: str = "This is a demo AI assistant using structured and simulated project data. It does not provide medical orders."



