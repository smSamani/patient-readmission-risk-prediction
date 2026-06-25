from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable

WEB_DEMO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = WEB_DEMO_ROOT / "diabetes_readmission_demo.sqlite"


def get_db_path() -> Path:
    return Path(os.getenv("DIABETES_READMISSION_DB", str(DEFAULT_DB_PATH))).expanduser()


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found at {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_one(query: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(query, tuple(params)).fetchone()


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(query, tuple(params)).fetchall()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)
