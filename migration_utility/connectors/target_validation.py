from __future__ import annotations

from typing import Any

from migration_utility.schema.target_registry import TargetSchemaRegistry, build_default_target_registry


def validate_against_target(
    records: list[dict[str, Any]],
    *,
    target_system: str,
    entity: str,
    registry: TargetSchemaRegistry | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    reg = registry or build_default_target_registry()
    schema = reg.get(target_system, entity)
    if not schema:
        return records, []

    required = {f.name for f in schema.fields if f.required}
    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []

    for record in records:
        missing = [name for name in required if not record.get(name)]
        if missing:
            invalid.append({**record, "_validation_errors": missing})
        else:
            valid.append(record)

    return valid, invalid
