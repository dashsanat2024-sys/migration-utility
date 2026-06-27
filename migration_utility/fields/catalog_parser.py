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

    if _looks_like_data_extract(rows):
        return _fields_from_data_extract(rows)

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


_CATALOG_HEADER_KEYS = frozenset({"name", "field_name", "field", "column"})


def _looks_like_data_extract(rows: list[dict[str, Any]]) -> bool:
    """True when CSV rows are records (extract) rather than field-definition rows."""
    if not rows:
        return False
    headers = {str(k).strip().lower() for k in rows[0].keys() if k}
    if not headers:
        return False
    if headers & _CATALOG_HEADER_KEYS:
        return False
    # Multi-column files without catalog headers are data extracts (e.g. Target/CMP export).
    return len(headers) >= 2


def _fields_from_data_extract(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Infer source field list from the header row of a tabular data extract."""
    headers = [str(k).strip() for k in rows[0].keys() if k and str(k).strip()]
    if not headers:
        raise ParseError("Data extract CSV has no column headers")
    fields: list[dict[str, Any]] = []
    for i, header in enumerate(headers):
        fields.append(
            _normalize_field(
                {
                    "name": header,
                    "data_type": _infer_column_type(header, rows),
                    "required": False,
                    "description": f"Column from data extract ({len(rows)} sample row(s))",
                },
                index=i,
            )
        )
    return fields


def _infer_column_type(column: str, rows: list[dict[str, Any]], *, sample_size: int = 20) -> str:
    """Best-effort type hint from column name and sample cell values."""
    col_upper = column.upper()
    if "DATE" in col_upper or col_upper.endswith("_DT"):
        return "date"
    if col_upper.endswith("_FLAG") or col_upper.startswith("FG_"):
        return "bool"
    if col_upper.endswith("_PENCE") or col_upper.endswith("_AMT") or col_upper.endswith("_BALANCE"):
        return "int"
    # Account / reference codes are strings even when numeric (leading zeros, padding).
    if "ACCOUNT" in col_upper or col_upper.endswith("_NO") or col_upper.endswith("_REF"):
        return "string"

    samples: list[str] = []
    for row in rows[:sample_size]:
        val = row.get(column)
        if val is None:
            continue
        text = str(val).strip()
        if text:
            samples.append(text)
    if not samples:
        return "string"

    if all(s.upper() in ("Y", "N", "YES", "NO", "TRUE", "FALSE", "1", "0") for s in samples):
        return "bool"
    if all(re.fullmatch(r"\d+", s) for s in samples):
        return "int"
    if all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) for s in samples):
        return "date"
    return "string"


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


# Known legacy extract column → Kraken AccountType socket aliases (Target/CMP QA sample).
_SOURCE_DEST_ALIASES: dict[str, tuple[str, ...]] = {
    "custaccountno": ("number",),
    "legacysysref": ("urn",),
    "steppedrateflag": ("isonsteppedtariff",),
    "acctstatuscode": ("status",),
    "docformatpref": ("documentaccessibility",),
    "custtypeflag": ("accounttype",),
    "addrline1": ("billingaddressline1", "addressline1"),
    "addrline2": ("billingaddressline2", "addressline2"),
    "addrpostcode": ("billingaddresspostcode", "addresspostcode"),
    "dateaccountopened": ("createdat",),
}


def _alias_score(source_name: str, dest_name: str) -> int:
    src_key = normalize_field_key(source_name)
    dest_key = normalize_field_key(dest_name)
    aliases = _SOURCE_DEST_ALIASES.get(src_key, ())
    if dest_key in aliases:
        return 95
    for alias in aliases:
        if alias in dest_key or dest_key in alias:
            return 85
    return 0


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


def suggest_schema_mappings(
    source_fields: list[dict[str, Any]],
    destination_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build destination-first mapping rows — each schema field is a socket."""
    source_pool = list(source_fields)
    used_sources: set[str] = set()
    rows: list[dict[str, Any]] = []

    def pick_source(dest_name: str) -> dict[str, Any] | None:
        dest_norm = normalize_field_key(dest_name)
        candidates: list[tuple[int, dict[str, Any]]] = []
        for sf in source_pool:
            if sf["name"] in used_sources:
                continue
            src_norm = normalize_field_key(sf["name"])
            score = 0
            if sf["name"] == dest_name:
                score = 100
            elif sf["name"].lower() == dest_name.lower():
                score = 90
            elif src_norm == dest_norm:
                score = 80
            elif src_norm in dest_norm or dest_norm in src_norm:
                score = 50
            alias = _alias_score(sf["name"], dest_name)
            if alias > score:
                score = alias
            if score:
                candidates.append((score, sf))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (-x[0], x[1]["name"]))
        return candidates[0][1]

    ordered = sorted(destination_fields, key=lambda f: (not f.get("required", False), f["name"]))
    for df in ordered:
        match = pick_source(df["name"])
        row = {
            "source_field": match["name"] if match else None,
            "source_type": match.get("data_type") if match else None,
            "source_required": match.get("required", False) if match else False,
            "target_field": df["name"],
            "target_type": df.get("data_type", "string"),
            "target_required": bool(df.get("required", False)),
            "target_description": df.get("description", ""),
            "target_constraints": df.get("constraints") or {},
            "transform_type": "copy",
            "config": {},
            "status": _schema_row_status(df, match),
            "match_confidence": "high" if match else "none",
        }
        if match:
            used_sources.add(match["name"])
        rows.append(row)

    for sf in source_pool:
        if sf["name"] not in used_sources:
            rows.append(
                {
                    "source_field": sf["name"],
                    "source_type": sf.get("data_type", "string"),
                    "source_required": sf.get("required", False),
                    "target_field": None,
                    "target_type": None,
                    "target_required": False,
                    "target_description": "",
                    "transform_type": "copy",
                    "config": {},
                    "status": "source_only",
                    "match_confidence": "none",
                }
            )

    return rows


def _schema_row_status(dest: dict[str, Any], source: dict[str, Any] | None) -> str:
    if source:
        return "mapped"
    if dest.get("required"):
        return "required_unmapped"
    return "optional_unmapped"
