from fastapi import APIRouter

from app.schemas import InterventionCreate, InterventionUpdate
from app.services.intervention_service import create_intervention, list_interventions, update_intervention

router = APIRouter(tags=["interventions"])


@router.get("/patients/{patient_id}/interventions")
def get_patient_interventions(patient_id: str) -> list[dict]:
    return list_interventions(patient_id)


@router.post("/patients/{patient_id}/interventions", status_code=201)
def post_patient_intervention(patient_id: str, payload: InterventionCreate) -> dict:
    return create_intervention(patient_id, payload.model_dump())


@router.patch("/interventions/{intervention_id}")
def patch_intervention(intervention_id: str, payload: InterventionUpdate) -> dict:
    return update_intervention(intervention_id, payload.model_dump(exclude_unset=True))
