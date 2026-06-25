from fastapi import APIRouter

from app.database import fetch_all, fetch_one
from app.services.patient_service import get_patient_keys

router = APIRouter(prefix="/patients", tags=["clinical"])


@router.get("/{patient_id}/clinical-review")
def clinical_review(patient_id: str) -> dict:
    keys = get_patient_keys(patient_id)
    review = fetch_one("SELECT * FROM clinical_reviews WHERE encounter_id = ?", [keys["encounter_id"]])
    timeline = fetch_all("SELECT * FROM diagnosis_timeline WHERE encounter_id = ? ORDER BY diagnosis_rank ASC", [keys["encounter_id"]])
    return {
        "clinical_review": dict(review) if review else None,
        "diagnosis_timeline": [dict(row) for row in timeline],
    }
