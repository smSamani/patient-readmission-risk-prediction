from fastapi import APIRouter

from app.database import get_connection, get_db_path

router = APIRouter()


@router.get("/health")
def api_health() -> dict:
    return {"status": "ok", "service": "diabetes-readmission-backend"}


@router.get("/db/health")
def db_health() -> dict:
    with get_connection() as conn:
        table_rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        counts = {}
        for row in table_rows:
            table = row["name"]
            counts[table] = conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
    return {"status": "ok", "database_path": str(get_db_path()), "table_counts": counts}
