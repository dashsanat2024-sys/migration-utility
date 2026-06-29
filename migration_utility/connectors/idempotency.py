"""Idempotency keys and URN dedup for destination loads."""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID


def external_id(record: dict[str, Any]) -> str:
    for key in (
        "accountId",
        "id",
        "KUNNR",
        "krakenAccountId",
        "sapCustomerNumber",
        "external_id",
    ):
        if record.get(key) is not None:
            return str(record[key])
    return "unknown"


def build_record_idempotency_key(
    project_id: UUID | str,
    entity: str,
    record: dict[str, Any],
) -> str:
    return f"{project_id}:{entity}:{external_id(record)}"


def build_batch_idempotency_key(
    project_id: UUID | str,
    entity: str,
    records: list[dict[str, Any]],
) -> str:
    parts = sorted(build_record_idempotency_key(project_id, entity, r) for r in records)
    digest = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return digest


def partition_idempotent(
    records: list[dict[str, Any]],
    already_loaded: set[str],
    *,
    entity: str,
    project_id: UUID | str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split records into to_load vs already-loaded (by external id URN)."""
    to_load: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for record in records:
        ext = external_id(record)
        if ext in already_loaded:
            skipped.append(
                {
                    **record,
                    "_idempotency_key": build_record_idempotency_key(project_id, entity, record),
                    "_skipped": True,
                    "_reason": "already_loaded",
                    "importStatus": "already_loaded",
                }
            )
        else:
            tagged = {
                **record,
                "_idempotency_key": build_record_idempotency_key(project_id, entity, record),
            }
            to_load.append(tagged)
    return to_load, skipped
