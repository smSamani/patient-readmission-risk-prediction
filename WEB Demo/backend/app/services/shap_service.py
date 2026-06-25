from app.database import fetch_all
from app.services.patient_service import get_patient_keys


def get_top3(patient_id: str) -> list[dict]:
    keys = get_patient_keys(patient_id)
    rows = fetch_all(
        """
        SELECT rank, feature, feature_label, feature_value, shap_value, effect_direction
        FROM shap_top3
        WHERE encounter_id = ?
        ORDER BY rank ASC
        """,
        [keys["encounter_id"]],
    )
    return [dict(row) for row in rows]


def get_all_features(patient_id: str) -> list[dict]:
    keys = get_patient_keys(patient_id)
    rows = fetch_all(
        """
        SELECT feature, feature_label, feature_value, shap_value, abs_shap_value, effect_direction
        FROM shap_all_features
        WHERE encounter_id = ?
        ORDER BY abs_shap_value DESC
        """,
        [keys["encounter_id"]],
    )
    return [dict(row) for row in rows]
