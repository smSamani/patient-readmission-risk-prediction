#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

DATE_FORMAT = "%Y-%m-%d"


@dataclass(frozen=True)
class TimelineContext:
    encounter_id: int
    scheduled_discharge_date: str | None
    time_in_hospital: int | None


def parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except ValueError:
        return None


def clamp_date(value, start, end):
    if value < start:
        return start
    if value > end:
        return end
    return value


def derive_date(context: TimelineContext, rank: int, existing_date: str | None):
    discharge_date = parse_date(context.scheduled_discharge_date)
    stay_days = context.time_in_hospital if isinstance(context.time_in_hospital, int) else None

    if discharge_date is None or stay_days is None or stay_days < 0:
        fallback = parse_date(existing_date) or discharge_date
        return fallback, "fallback_missing_context"

    admission_date = discharge_date - timedelta(days=max(stay_days, 0))
    if rank == 1:
        candidate = admission_date
    elif rank == 2:
        candidate = admission_date + timedelta(days=max(stay_days // 2, 0))
    elif rank == 3:
        candidate = discharge_date - timedelta(days=1) if stay_days > 0 else admission_date
    else:
        candidate = admission_date

    repaired = clamp_date(candidate, admission_date, discharge_date)
    return repaired, "derived"


def repair_database(db_path: Path) -> dict[str, int]:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    stats = {"rows_seen": 0, "rows_updated": 0, "fallback_rows": 0}

    try:
        rows = conn.execute(
            """
            SELECT
              dt.encounter_id,
              dt.diagnosis_rank,
              dt.date_recorded,
              sc.scheduled_discharge_date,
              e.time_in_hospital
            FROM diagnosis_timeline dt
            LEFT JOIN synthetic_context sc ON sc.encounter_id = dt.encounter_id
            LEFT JOIN encounters e ON e.encounter_id = dt.encounter_id
            ORDER BY dt.encounter_id, dt.diagnosis_rank
            """
        ).fetchall()

        for row in rows:
            stats["rows_seen"] += 1
            context = TimelineContext(
                encounter_id=row["encounter_id"],
                scheduled_discharge_date=row["scheduled_discharge_date"],
                time_in_hospital=row["time_in_hospital"],
            )
            repaired_date, mode = derive_date(context, int(row["diagnosis_rank"]), row["date_recorded"])
            if repaired_date is None:
                stats["fallback_rows"] += 1
                continue

            repaired_value = repaired_date.strftime(DATE_FORMAT)
            if repaired_value != row["date_recorded"]:
                conn.execute(
                    """
                    UPDATE diagnosis_timeline
                    SET date_recorded = ?
                    WHERE encounter_id = ? AND diagnosis_rank = ?
                    """,
                    (repaired_value, row["encounter_id"], row["diagnosis_rank"]),
                )
                stats["rows_updated"] += 1

            if mode != "derived":
                stats["fallback_rows"] += 1

        conn.commit()
        return stats
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair synthetic diagnosis timeline dates for the web demo SQLite database.")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "diabetes_readmission_demo.sqlite",
        help="Path to diabetes_readmission_demo.sqlite",
    )
    args = parser.parse_args()

    stats = repair_database(args.db)
    print(f"Diagnosis timeline date repair complete for {args.db}")
    print(f"Rows seen: {stats['rows_seen']}")
    print(f"Rows updated: {stats['rows_updated']}")
    print(f"Fallback rows: {stats['fallback_rows']}")


if __name__ == "__main__":
    main()
