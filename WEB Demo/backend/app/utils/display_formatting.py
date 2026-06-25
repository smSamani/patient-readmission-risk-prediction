from __future__ import annotations

import hashlib
import re
from typing import Any

SPECIAL_LABELS = {
    "Emergency_Room": "Emergency Room",
    "Nursing_Facility_or_Transfer": "Nursing Facility or Transfer",
    "Transfer_Other": "Other Transfer",
    "Emergency_Urgent": "Emergency or Urgent",
    "Other_Unknown": "Other or Unknown",
}

LOWERCASE_WORDS = {"or", "and", "of", "to", "with", "from"}


def format_display_label(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return stripped
    if stripped in SPECIAL_LABELS:
        return SPECIAL_LABELS[stripped]

    normalized = stripped.replace("_", " ").replace("/", " / ")
    words = []
    for word in normalized.split():
        if word.lower() in LOWERCASE_WORDS:
            words.append(word.lower())
        elif word.isupper():
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:])
    return " ".join(words)


def parse_age_band(age_band: str | None) -> tuple[int, int] | None:
    if not age_band:
        return None
    match = re.match(r"\[(\d+)-(\d+)\)", str(age_band).strip())
    if not match:
        return None
    lower = int(match.group(1))
    upper_exclusive = int(match.group(2))
    if upper_exclusive <= lower:
        return None
    return lower, upper_exclusive - 1


def derive_display_age(age_band: str | None, stable_key: str | int | None) -> int | None:
    bounds = parse_age_band(age_band)
    if bounds is None:
        return None
    lower, upper = bounds
    span = upper - lower + 1
    key = f"{stable_key or ''}|{age_band}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    offset = int(digest[:8], 16) % span
    return lower + offset


def add_display_label_fields(row: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    for field in fields:
        raw_value = row.get(field)
        row[f"{field}_raw"] = raw_value
        row[field] = format_display_label(raw_value)
    return row


def add_display_age_fields(row: dict[str, Any], age_field: str = "age", stable_key_field: str = "patient_id") -> dict[str, Any]:
    age_band = row.get(age_field)
    stable_key = row.get(stable_key_field) or row.get("encounter_id") or row.get("model_row_id")
    row["age_band"] = age_band
    row["display_age"] = derive_display_age(age_band, stable_key)
    return row
