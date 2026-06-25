from fastapi import APIRouter

from app.services.shap_service import get_all_features, get_top3

router = APIRouter(prefix="/patients", tags=["shap"])


@router.get("/{patient_id}/shap/top3")
def shap_top3(patient_id: str) -> list[dict]:
    return get_top3(patient_id)


@router.get("/{patient_id}/shap/all")
def shap_all(patient_id: str) -> list[dict]:
    return get_all_features(patient_id)
