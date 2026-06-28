from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.api.deps import get_db_session
from migration_utility.auth.deps import get_current_user, get_optional_user
from migration_utility.config import get_settings
from migration_utility.datastore.models import ExceptionItem, Project, User
from migration_utility.exceptions.service import ExceptionQueueService

router = APIRouter(prefix="/projects/{project_id}/exceptions", tags=["exceptions"])


class ExceptionItemRead(BaseModel):
    id: UUID
    project_id: UUID
    run_id: UUID | None
    ingest_error_id: UUID | None
    entity: str
    source_type: str
    row_number: int | None
    payload: dict
    error_reason: str
    status: str
    assigned_to_id: UUID | None
    override_payload: dict | None
    resolution_note: str | None
    history: list
    kraken_error_code: str | None = None
    root_cause_category: str | None = None
    owner_role: str | None = None
    remediation_hint: str | None = None
    fallout_status: str = "open"

    model_config = {"from_attributes": True}


class AssignRequest(BaseModel):
    user_id: UUID


class OverrideRequest(BaseModel):
    override_payload: dict = Field(default_factory=dict)
    note: str = ""


class ResolveRequest(BaseModel):
    note: str = ""


@router.get("", response_model=list[ExceptionItemRead])
def list_exceptions(
    project_id: UUID,
    status: str | None = None,
    db: Session = Depends(get_db_session),
) -> list[ExceptionItem]:
    _get_project(project_id, db)
    return ExceptionQueueService(db).list_for_project(project_id, status=status)


@router.post("/{exception_id}/assign", response_model=ExceptionItemRead)
def assign_exception(
    project_id: UUID,
    exception_id: UUID,
    body: AssignRequest,
    db: Session = Depends(get_db_session),
    actor: User | None = Depends(get_optional_user),
) -> ExceptionItem:
    if get_settings().auth_enabled and not actor:
        raise HTTPException(status_code=401, detail="Authentication required")
    item = _get_item(project_id, exception_id, db)
    assignee = db.get(User, body.user_id)
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found")
    return ExceptionQueueService(db).assign(item, assignee, actor=actor or assignee)


@router.post("/{exception_id}/override", response_model=ExceptionItemRead)
def override_exception(
    project_id: UUID,
    exception_id: UUID,
    body: OverrideRequest,
    db: Session = Depends(get_db_session),
    actor: User | None = Depends(get_optional_user),
) -> ExceptionItem:
    if get_settings().auth_enabled and not actor:
        raise HTTPException(status_code=401, detail="Authentication required")
    item = _get_item(project_id, exception_id, db)
    effective_actor = actor or db.scalar(select(User).limit(1))
    if not effective_actor:
        raise HTTPException(status_code=400, detail="No users available — enable auth and seed admin")
    return ExceptionQueueService(db).override(
        item, actor=effective_actor, override_payload=body.override_payload, note=body.note
    )


@router.post("/{exception_id}/resolve", response_model=ExceptionItemRead)
def resolve_exception(
    project_id: UUID,
    exception_id: UUID,
    body: ResolveRequest,
    db: Session = Depends(get_db_session),
    actor: User | None = Depends(get_optional_user),
) -> ExceptionItem:
    if get_settings().auth_enabled and not actor:
        raise HTTPException(status_code=401, detail="Authentication required")
    item = _get_item(project_id, exception_id, db)
    effective_actor = actor or db.scalar(select(User).limit(1))
    if not effective_actor:
        raise HTTPException(status_code=400, detail="No users available — enable auth and seed admin")
    return ExceptionQueueService(db).resolve(item, actor=effective_actor, note=body.note)


@router.post("/sync-ingest", response_model=list[ExceptionItemRead])
def sync_ingest_errors(
    project_id: UUID,
    db: Session = Depends(get_db_session),
) -> list[ExceptionItem]:
    from migration_utility.datastore.models import IngestError

    _get_project(project_id, db)
    svc = ExceptionQueueService(db)
    errors = list(
        db.scalars(
            select(IngestError).where(
                IngestError.project_id == project_id,
                IngestError.resolved.is_(False),
            )
        )
    )
    items = [svc.sync_from_ingest_error(e) for e in errors]
    db.commit()
    return items


def _get_project(project_id: UUID, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_item(project_id: UUID, exception_id: UUID, db: Session) -> ExceptionItem:
    item = db.get(ExceptionItem, exception_id)
    if not item or item.project_id != project_id:
        raise HTTPException(status_code=404, detail="Exception not found")
    return item
