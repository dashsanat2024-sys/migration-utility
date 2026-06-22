from __future__ import annotations

import csv
import json
import re
from io import StringIO
from typing import Any

from migration_utility.ingest.parsers import ParseError, detect_format, parse_csv


def parse_field_catalog(text: str, *, filename: str, content_type: str | None = None) -> list[dict[str, Any]]:
    """Parse a field-definition file (CSV or JSON) into normalized field dicts."""
    fmt = detect_format(filename, content_type)
    if fmt == "json":
        return _parse_field_json(text)
    if fmt == "csv":
        return _parse_field_csv(text)
    raise ParseError(f"Unsupported field catalog format: {fmt!r}")


def _parse_field_json(text: str) -> list[dict[str, Any]]:
    data = json.loads(text)
    if isinstance(data, dict) and "fields" in data:
        data = data["fields"]
    if not isinstance(data, list):
        raise ParseError("JSON field catalog must be an array or {fields: [...]}")
    return [_normalize_field(item, index=i) for i, item in enumerate(data)]


def _parse_field_csv(text: str) -> list[dict[str, Any]]:
    rows = parse_csv(text)
    if not rows:
        raise ParseError("Field catalog CSV is empty")

    fields: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        name = (
            row.get("name")
            or row.get("field_name")
            or row.get("field")
            or row.get("column")
            or next(iter(row.values()), None)
        )
        if not name or not str(name).strip():
            continue
        fields.append(
            _normalize_field(
                {
                    "name": str(name).strip(),
                    "data_type": row.get("data_type") or row.get("type") or "string",
                    "required": row.get("required"),
                    "description": row.get("description") or row.get("desc") or "",
                },
                index=i,
            )
        )

    if not fields:
        # Single-column list without header names we recognize
        reader = csv.reader(StringIO(text))
        for i, row in enumerate(reader):
            if not row or not row[0].strip():
                continue
            header = row[0].strip().lower()
            if i == 0 and header in ("name", "field", "field_name", "column"):
                continue
            fields.append(_normalize_field({"name": row[0].strip()}, index=i))

    if not fields:
        raise ParseError("No field names found in catalog file")
    return fields


def _normalize_field(raw: Any, *, index: int) -> dict[str, Any]:
    if isinstance(raw, str):
        raw = {"name": raw}
    if not isinstance(raw, dict):
        raise ParseError(f"Field entry at index {index} must be an object or string")
    name = raw.get("name") or raw.get("field_name")
    if not name:
        raise ParseError(f"Field entry at index {index} is missing name")
    required = raw.get("required", False)
    if isinstance(required, str):
        required = required.strip().lower() in ("true", "1", "yes", "y")
    return {
        "name": str(name).strip(),
        "data_type": str(raw.get("data_type") or raw.get("type") or "string").strip().lower(),
        "required": bool(required),
        "description": str(raw.get("description") or raw.get("desc") or "").strip(),
    }


def normalize_field_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def suggest_field_mappings(
    source_fields: list[dict[str, Any]],
    target_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Suggest source→target pairs by exact and normalized name match."""
    target_pool = list(target_fields)
    used: set[str] = set()
    suggestions: list[dict[str, Any]] = []

    def pick_target(source_name: str) -> dict[str, Any] | None:
        src_norm = normalize_field_key(source_name)
        candidates: list[tuple[int, dict[str, Any]]] = []
        for tf in target_pool:
            if tf["name"] in used:
                continue
            tgt_norm = normalize_field_key(tf["name"])
            score = 0
            if source_name == tf["name"]:
                score = 100
            elif source_name.lower() == tf["name"].lower():
                score = 90
            elif src_norm == tgt_norm:
                score = 80
            elif src_norm in tgt_norm or tgt_norm in src_norm:
                score = 50
            if score:
                candidates.append((score, tf))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x[0], x[1]["name"]))
        return candidates[0][1]

    for sf in source_fields:
        match = pick_target(sf["name"])
        row = {
            "source_field": sf["name"],
            "source_type": sf.get("data_type", "string"),
            "source_required": sf.get("required", False),
            "target_field": match["name"] if match else None,
            "target_type": match.get("data_type") if match else None,
            "transform_type": "copy",
            "config": {},
            "status": "suggested" if match else "unmapped",
            "match_confidence": "high" if match else "none",
        }
        if match:
            used.add(match["name"])
        suggestions.append(row)

    for tf in target_pool:
        if tf["name"] not in used:
            suggestions.append(
                {
                    "source_field": None,
                    "source_type": None,
                    "source_required": False,
                    "target_field": tf["name"],
                    "target_type": tf.get("data_type", "string"),
                    "transform_type": "constant",
                    "config": {},
                    "status": "target_only",
                    "match_confidence": "none",
                }
            )

    return suggestions
