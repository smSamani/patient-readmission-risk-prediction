from fastapi import APIRouter

from app.services.patient_service import get_summary

router = APIRouter(tags=["summary"])


@router.get("/summary")
def summary() -> dict:
    return get_summary()
