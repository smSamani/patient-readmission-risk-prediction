from __future__ import annotations

from datetime import datetime
from typing import Any

from app.database import fetch_all, fetch_one, get_connection
from app.services.patient_service import get_patient_keys
from app.utils.errors import not_found

USER_INTERVENTION_STATUSES = ("planned", "in_progress", "completed", "cancelled")
_STATUS_PLACEHOLDERS = ", ".join("?" for _ in USER_INTERVENTION_STATUSES)


def _with_user_flags(row: dict[str, Any]) -> dict[str, Any]:
    row["source_type"] = "user_saved"
    row["is_user_created"] = True
    row["is_editable"] = True
    return row


def list_interventions(patient_id: str) -> list[dict[str, Any]]:
    keys = get_patient_keys(patient_id)
    rows = fetch_all(
        f"""
        SELECT * FROM interventions
        WHERE encounter_id = ? AND intervention_status IN ({_STATUS_PLACEHOLDERS})
        ORDER BY created_at DESC, intervention_id ASC
        """,
        [keys["encounter_id"], *USER_INTERVENTION_STATUSES],
    )
    return [_with_user_flags(dict(row)) for row in rows]


def _next_intervention_id(conn) -> str:
    row = conn.execute("SELECT intervention_id FROM interventions ORDER BY intervention_id DESC LIMIT 1").fetchone()
    if not row:
        return "INT-0001"
    try:
        next_num = int(str(row["intervention_id"]).split("-")[-1]) + 1
    except ValueError:
        next_num = int(datetime.utcnow().timestamp())
    return f"INT-{next_num:04d}"


def create_intervention(patient_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    keys = get_patient_keys(patient_id)
    with get_connection() as conn:
        intervention_id = _next_intervention_id(conn)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn.execute(
            """
            INSERT INTO interventions (intervention_id, encounter_id, intervention_type, intervention_status, created_by, created_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                intervention_id,
                keys["encounter_id"],
                payload["intervention_type"],
                payload["intervention_status"],
                payload["created_by"],
                created_at,
                payload.get("notes"),
            ],
        )
        conn.commit()
        row = conn.execute("SELECT * FROM interventions WHERE intervention_id = ?", [intervention_id]).fetchone()
    return _with_user_flags(dict(row))


def update_intervention(intervention_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    updates = {k: v for k, v in payload.items() if v is not None}
    if not updates:
        row = fetch_one(
            f"SELECT * FROM interventions WHERE intervention_id = ? AND intervention_status IN ({_STATUS_PLACEHOLDERS})",
            [intervention_id, *USER_INTERVENTION_STATUSES],
        )
        if row is None:
            raise not_found("Intervention not found or not editable")
        return _with_user_flags(dict(row))

    allowed = {"intervention_status", "notes", "created_by"}
    set_parts = []
    params = []
    for key, value in updates.items():
        if key in allowed:
            set_parts.append(f"{key} = ?")
            params.append(value)
    if not set_parts:
        raise not_found("Intervention not found or not editable")

    with get_connection() as conn:
        existing = conn.execute(
            f"SELECT * FROM interventions WHERE intervention_id = ? AND intervention_status IN ({_STATUS_PLACEHOLDERS})",
            [intervention_id, *USER_INTERVENTION_STATUSES],
        ).fetchone()
        if existing is None:
            raise not_found("Intervention not found or not editable")
        conn.execute(f"UPDATE interventions SET {', '.join(set_parts)} WHERE intervention_id = ?", [*params, intervention_id])
        conn.commit()
        row = conn.execute("SELECT * FROM interventions WHERE intervention_id = ?", [intervention_id]).fetchone()
    return _with_user_flags(dict(row))
