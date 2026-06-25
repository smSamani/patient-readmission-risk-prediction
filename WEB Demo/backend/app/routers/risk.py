from fastapi import APIRouter

from app.database import fetch_one
from app.services.patient_service import get_patient_keys
from app.utils.errors import not_found

router = APIRouter(prefix="/patients", tags=["risk"])


@router.get("/{patient_id}/risk")
def patient_risk(patient_id: str) -> dict:
    keys = get_patient_keys(patient_id)
    row = fetch_one(
        """
        SELECT actual_readmitted_30d, predicted_probability_calibrated, calibrated_risk_pct,
               risk_category, predicted_class
        FROM risk_predictions
        WHERE encounter_id = ?
        """,
        [keys["encounter_id"]],
    )
    if row is None:
        raise not_found("Risk prediction not found")
    return dict(row)
