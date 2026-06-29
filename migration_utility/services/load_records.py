from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.datastore.models import LoadRecord, Project


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
    ) -> int:
        count = 0
        for record in loaded:
            self._db.add(
                LoadRecord(
                    project_id=project.id,
                    run_id=run_id,
                    batch_id=batch_id,
                    target_adapter_key=target_adapter_key,
                    entity=entity,
                    external_id=_external_id(record),
                    idempotency_key=record.get("_idempotency_key"),
                    status="loaded",
                    request_payload=_strip_internal(record),
                    response_payload=record,
                )
            )
            count += 1

        for record in failed:
            error = record.get("_error") or record.get("_validation_errors")
            self._db.add(
                LoadRecord(
                    project_id=project.id,
                    run_id=run_id,
                    batch_id=batch_id,
                    target_adapter_key=target_adapter_key,
                    entity=entity,
                    external_id=_external_id(record),
                    idempotency_key=record.get("_idempotency_key"),
                    status="failed",
                    request_payload=_strip_internal(record),
                    error_message=str(error) if error else "Load failed",
                )
            )
            count += 1

        if count:
            self._db.flush()
        return count

    def list_for_run(self, run_id: UUID) -> list[LoadRecord]:
        stmt = (
            select(LoadRecord)
            .where(LoadRecord.run_id == run_id)
            .order_by(LoadRecord.external_id)
        )
        return list(self._db.scalars(stmt))

    def list_for_project(
        self, project_id: UUID, *, limit: int = 200
    ) -> list[LoadRecord]:
        stmt = (
            select(LoadRecord)
            .where(LoadRecord.project_id == project_id)
            .order_by(LoadRecord.created_at.desc())
            .limit(limit)
        )
        return list(self._db.scalars(stmt))

    def summary_for_run(self, run_id: UUID) -> dict[str, int]:
        records = self.list_for_run(run_id)
        loaded = sum(1 for r in records if r.status == "loaded")
        failed = sum(1 for r in records if r.status == "failed")
        return {"loaded": loaded, "failed": failed, "total": len(records)}


def _strip_internal(record: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in record.items() if not str(k).startswith("_")}
