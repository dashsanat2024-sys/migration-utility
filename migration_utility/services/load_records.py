"""Bulk load-record persistence and audit modes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.config import get_settings
from migration_utility.datastore.base import new_uuid
from migration_utility.datastore.models import LoadRecord, Project

AuditMode = Literal["full", "summary"]


def _external_id(record: dict[str, Any]) -> str:
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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _strip_internal(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if not str(k).startswith("_")}


class LoadRecordService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def loaded_external_ids(self, project_id: UUID, *, entity: str) -> set[str]:
        stmt = select(LoadRecord.external_id).where(
            LoadRecord.project_id == project_id,
            LoadRecord.entity == entity,
            LoadRecord.status == "loaded",
        )
        return set(self._db.scalars(stmt))

    def persist_results(
        self,
        project: Project,
        *,
        run_id: UUID | None,
        batch_id: UUID | None,
        target_adapter_key: str,
        entity: str,
        loaded: list[dict[str, Any]],
        failed: list[dict[str, Any]],
        audit_mode: AuditMode | None = None,
        sample_size: int | None = None,
    ) -> int:
        settings = get_settings()
        mode: AuditMode = audit_mode or settings.load_audit_mode  # type: ignore[assignment]
        sample_size = sample_size if sample_size is not None else settings.load_audit_sample_size

        loaded_total = len(loaded)
        failed_total = len(failed)
        if mode == "summary":
            loaded = loaded[:sample_size]
            failed = failed[:sample_size]

        mappings = self._build_mappings(
            project=project,
            run_id=run_id,
            batch_id=batch_id,
            target_adapter_key=target_adapter_key,
            entity=entity,
            loaded=loaded,
            failed=failed,
        )

        if mode == "summary" and (loaded_total or failed_total):
            mappings.append(
                self._summary_mapping(
                    project=project,
                    run_id=run_id,
                    batch_id=batch_id,
                    target_adapter_key=target_adapter_key,
                    entity=entity,
                    loaded_total=loaded_total,
                    failed_total=failed_total,
                    samples_persisted=len(loaded) + len(failed),
                )
            )

        if not mappings:
            return 0

        self._db.bulk_insert_mappings(LoadRecord, mappings)
        self._db.flush()
        return len(mappings)

    def _build_mappings(
        self,
        *,
        project: Project,
        run_id: UUID | None,
        batch_id: UUID | None,
        target_adapter_key: str,
        entity: str,
        loaded: list[dict[str, Any]],
        failed: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        now = _utcnow()
        mappings: list[dict[str, Any]] = []

        for record in loaded:
            mappings.append(
                {
                    "id": new_uuid(),
                    "project_id": project.id,
                    "run_id": run_id,
                    "batch_id": batch_id,
                    "target_adapter_key": target_adapter_key,
                    "entity": entity,
                    "external_id": _external_id(record),
                    "idempotency_key": record.get("_idempotency_key"),
                    "status": "loaded",
                    "request_payload": _strip_internal(record),
                    "response_payload": record,
                    "error_message": None,
                    "created_at": now,
                    "updated_at": now,
                }
            )

        for record in failed:
            error = record.get("_error") or record.get("_validation_errors")
            mappings.append(
                {
                    "id": new_uuid(),
                    "project_id": project.id,
                    "run_id": run_id,
                    "batch_id": batch_id,
                    "target_adapter_key": target_adapter_key,
                    "entity": entity,
                    "external_id": _external_id(record),
                    "idempotency_key": record.get("_idempotency_key"),
                    "status": "failed",
                    "request_payload": _strip_internal(record),
                    "response_payload": None,
                    "error_message": str(error) if error else "Load failed",
                    "created_at": now,
                    "updated_at": now,
                }
            )

        return mappings

    def _summary_mapping(
        self,
        *,
        project: Project,
        run_id: UUID | None,
        batch_id: UUID | None,
        target_adapter_key: str,
        entity: str,
        loaded_total: int,
        failed_total: int,
        samples_persisted: int,
    ) -> dict[str, Any]:
        now = _utcnow()
        return {
            "id": new_uuid(),
            "project_id": project.id,
            "run_id": run_id,
            "batch_id": batch_id,
            "target_adapter_key": target_adapter_key,
            "entity": entity,
            "external_id": "__audit_summary__",
            "idempotency_key": None,
            "status": "audit_summary",
            "request_payload": None,
            "response_payload": {
                "loaded": loaded_total,
                "failed": failed_total,
                "samples_persisted": samples_persisted,
                "audit_mode": "summary",
            },
            "error_message": None,
            "created_at": now,
            "updated_at": now,
        }

    def list_for_run(self, run_id: UUID) -> list[LoadRecord]:
        stmt = (
            select(LoadRecord)
            .where(LoadRecord.run_id == run_id)
            .where(LoadRecord.status != "audit_summary")
            .order_by(LoadRecord.external_id)
        )
        return list(self._db.scalars(stmt))

    def list_for_project(
        self, project_id: UUID, *, limit: int = 200
    ) -> list[LoadRecord]:
        stmt = (
            select(LoadRecord)
            .where(LoadRecord.project_id == project_id)
            .where(LoadRecord.status != "audit_summary")
            .order_by(LoadRecord.created_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def summary_for_run(self, run_id: UUID) -> dict[str, int | str]:
        summary_rows = list(
            self._db.scalars(
                select(LoadRecord).where(
                    LoadRecord.run_id == run_id,
                    LoadRecord.status == "audit_summary",
                )
            )
        )
        if summary_rows:
            loaded = sum(int((r.response_payload or {}).get("loaded", 0)) for r in summary_rows)
            failed = sum(int((r.response_payload or {}).get("failed", 0)) for r in summary_rows)
            return {
                "loaded": loaded,
                "failed": failed,
                "total": loaded + failed,
                "audit_mode": "summary",
            }

        records = list(
            self._db.scalars(select(LoadRecord).where(LoadRecord.run_id == run_id))
        )
        loaded = sum(1 for r in records if r.status == "loaded")
        failed = sum(1 for r in records if r.status == "failed")
        return {"loaded": loaded, "failed": failed, "total": len(records), "audit_mode": "full"}
