from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from migration_utility.schema.registry import SchemaEntity, SchemaField


def validate_records(
    entity: SchemaEntity,
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[tuple[int, dict[str, Any], str]]]:
    """
    Validate and coerce records against a schema entity.

    Returns (valid_records, errors) where errors are (row_number, raw_record, reason).
    """
    valid: list[dict[str, Any]] = []
    errors: list[tuple[int, dict[str, Any], str]] = []

    for idx, raw in enumerate(records, start=1):
        coerced, err = _validate_one(entity, raw)
        if err:
            errors.append((idx, raw, err))
        else:
            valid.append(coerced)

    return valid, errors


def _validate_one(
    entity: SchemaEntity,
    raw: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    coerced: dict[str, Any] = {}
    for field in entity.fields:
        value = raw.get(field.name)
        if _is_empty(value):
            if field.required:
                return None, f"Missing required field: {field.name}"
            coerced[field.name] = None
            continue
        try:
            coerced[field.name] = _coerce(field, value)
        except ValueError as exc:
            return None, f"Field {field.name}: {exc}"
    return coerced, None


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _coerce(field: SchemaField, value: Any) -> Any:
    dt = field.data_type.lower()
    if dt == "string":
        return str(value).strip()
    if dt == "integer":
        return int(value)
    if dt == "decimal":
        return Decimal(str(value))
    if dt == "boolean":
        if isinstance(value, bool):
            return value
        normalized = str(value).strip().lower()
        if normalized in ("true", "1", "yes", "y"):
            return True
        if normalized in ("false", "0", "no", "n"):
            return False
        raise ValueError(f"invalid boolean {value!r}")
    if dt == "date":
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value).strip()[:10])
    if dt == "datetime":
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).strip())
    return value
