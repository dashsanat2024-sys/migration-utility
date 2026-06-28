from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.datastore.models import ExceptionItem, IngestError, User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _append_history(item: ExceptionItem, *, actor_id: UUID | None, action: str, note: str = "") -> None:
    item.history = [
        *(item.history or []),
        {
            "at": _utcnow().isoformat(),
            "actor_id": str(actor_id) if actor_id else None,
            "action": action,
            "note": note,
        },
    ]


class ExceptionQueueService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_project(
        self,
        project_id: UUID,
        *,
        status: str | None = None,
        assigned_to_id: UUID | None = None,
    ) -> list[ExceptionItem]:
        stmt = select(ExceptionItem).where(ExceptionItem.project_id == project_id)
        if status:
            stmt = stmt.where(ExceptionItem.status == status)
        if assigned_to_id:
            stmt = stmt.where(ExceptionItem.assigned_to_id == assigned_to_id)
        stmt = stmt.order_by(ExceptionItem.created_at.desc())
        return list(self._db.scalars(stmt))

    def sync_from_ingest_error(self, error: IngestError) -> ExceptionItem:
        existing = self._db.scalar(
            select(ExceptionItem).where(ExceptionItem.ingest_error_id == error.id)
        )
        if existing:
            return existing
        item = ExceptionItem(
            project_id=error.project_id,
            ingest_error_id=error.id,
            entity=error.entity,
            source_type="ingest",
            row_number=error.row_number,
            payload=error.raw_payload,
            error_reason=error.error_reason,
            status="open" if not error.resolved else "resolved",
        )
        self._db.add(item)
        self._db.flush()
        return item

    def create_validation_exception(
        self,
        *,
        project_id: UUID,
        run_id: UUID | None,
        entity: str,
        row_number: int | None,
        payload: dict,
        error_reason: str,
    ) -> ExceptionItem:
        item = ExceptionItem(
            project_id=project_id,
            run_id=run_id,
            entity=entity,
            source_type="validation",
            row_number=row_number,
            payload=payload,
            error_reason=error_reason,
            status="open",
        )
        self._db.add(item)
        self._db.flush()
        return item

    def assign(self, item: ExceptionItem, user: User, *, actor: User) -> ExceptionItem:
        item.assigned_to_id = user.id
        item.status = "assigned"
        _append_history(item, actor_id=actor.id, action="assigned", note=f"Assigned to {user.email}")
        self._db.flush()
        return item

    def override(
        self,
        item: ExceptionItem,
        *,
        actor: User,
        override_payload: dict,
        note: str,
    ) -> ExceptionItem:
        item.override_payload = override_payload
        item.status = "overridden"
        item.resolution_note = note
        _append_history(item, actor_id=actor.id, action="override", note=note)
        self._db.flush()
        return item

    def resolve(self, item: ExceptionItem, *, actor: User, note: str = "") -> ExceptionItem:
        item.status = "resolved"
        item.resolution_note = note or item.resolution_note
        _append_history(item, actor_id=actor.id, action="resolved", note=note)
        if item.ingest_error_id:
            err = self._db.get(IngestError, item.ingest_error_id)
            if err:
                err.resolved = True
        self._db.flush()
        return item
