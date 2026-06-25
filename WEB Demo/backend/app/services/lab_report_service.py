from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Any


def _candidate_manifest_paths() -> list[Path]:
    root = Path(__file__).resolve().parents[3]
    return [
        root / "frontend" / "public" / "lab_reports" / "lab_report_manifest.csv",
        root / "lab_report_package_for_codex" / "lab_report_manifest.csv",
    ]


@lru_cache(maxsize=1)
def get_lab_report_manifest() -> list[dict[str, str]]:
    for path in _candidate_manifest_paths():
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    return []


def get_lab_report_patient_ids(filters: dict[str, Any] | None = None) -> set[str]:
    filters = filters or {}
    report_type = str(filters.get("lab_report_type") or "").strip().upper()
    status = str(filters.get("lab_report_status") or "").strip().lower()
    source_basis = str(filters.get("lab_report_source_basis") or "").strip().lower()

    patient_ids: set[str] = set()
    for row in get_lab_report_manifest():
        if report_type and str(row.get("report_type") or "").upper() != report_type:
            continue
        if status and str(row.get("status_label") or "").lower() != status:
            continue
        if source_basis and str(row.get("source_basis") or "").lower() != source_basis:
            continue
        patient_id = str(row.get("patient_id") or "").strip()
        if patient_id:
            patient_ids.add(patient_id)
    return patient_ids


def get_lab_report_capabilities() -> dict[str, Any]:
    rows = get_lab_report_manifest()
    return {
        "patient_ids_with_lab_reports": sorted({row["patient_id"] for row in rows if row.get("patient_id")}),
        "report_types": sorted({row["report_type"] for row in rows if row.get("report_type")}),
        "status_labels": sorted({row["status_label"] for row in rows if row.get("status_label")}),
        "source_basis_values": sorted({row["source_basis"] for row in rows if row.get("source_basis")}),
    }
