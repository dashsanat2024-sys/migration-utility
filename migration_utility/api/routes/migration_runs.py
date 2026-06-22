from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from migration_utility.api.deps import get_db_session, get_registry
from migration_utility.api.schemas import AuditLogRead, LoadRecordRead, LoadSummaryRead, MigrationRunCreate, MigrationRunRead
from migration_utility.connectors.registry import ConnectorRegistry
from migration_utility.core.enums import AuditAction
from migration_utility.datastore.models import AuditLog, Batch, MigrationRun, Project
from migration_utility.services.audit import write_audit
from migration_utility.services.load_records import LoadRecordService
from migration_utility.services.runner import RunService

router = APIRouter(tags=["migration-runs"])


@router.post(
    "/projects/{project_id}/runs",
    response_model=MigrationRunRead,
    status_code=status.HTTP_201_CREATED,
)
def create_migration_run(
    project_id: UUID,
    body: MigrationRunCreate,
    db: Session = Depends(get_db_session),
    registry: ConnectorRegistry = Depends(get_registry),
) -> MigrationRun:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for key in (project.source_connector_key, project.target_adapter_key):
        try:
            if key in registry.list_sources() or key in registry.list_targets():
                continue
        except Exception:
            pass
    if project.source_connector_key not in registry.list_sources():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown source connector: {project.source_connector_key!r}",
        )
    if project.target_adapter_key not in registry.list_targets():
        raise HTTPException(
            status_code=400,
            detail=f"Unknown target adapter: {project.target_adapter_key!r}",
        )

    run = MigrationRun(
        project_id=project.id,
        name=body.name,
        run_config=body.run_config,
    )
    for batch_in in body.batches:
        run.batches.append(
            Batch(batch_number=batch_in.batch_number, batch_config=batch_in.batch_config)
        )
    db.add(run)
    db.flush()
    write_audit(
        db,
        entity_type="migration_run",
        entity_id=str(run.id),
        action=AuditAction.CREATED,
        message=f"Run {run.name} created",
        project_id=project.id,
        run_id=run.id,
    )
    db.commit()
    db.refresh(run)

    service = RunService(db, registry)
    run = service.execute_run(run, project)
    return _load_run(db, run.id)


@router.get("/projects/{project_id}/runs", response_model=list[MigrationRunRead])
def list_migration_runs(
    project_id: UUID, db: Session = Depends(get_db_session)
) -> list[MigrationRun]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    stmt = (
        select(MigrationRun)
        .where(MigrationRun.project_id == project_id)
        .options(selectinload(MigrationRun.batches))
        .order_by(MigrationRun.created_at.desc())
    )
    return list(db.scalars(stmt))


@router.get("/runs/{run_id}", response_model=MigrationRunRead)
def get_migration_run(run_id: UUID, db: Session = Depends(get_db_session)) -> MigrationRun:
    run = _load_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Migration run not found")
    return run


@router.get("/runs/{run_id}/audit", response_model=list[AuditLogRead])
def get_run_audit_log(run_id: UUID, db: Session = Depends(get_db_session)) -> list[AuditLog]:
    run = db.get(MigrationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Migration run not found")
    stmt = (
        select(AuditLog)
        .where(AuditLog.run_id == run_id)
        .order_by(AuditLog.created_at.asc())
    )
    return list(db.scalars(stmt))


@router.get("/runs/{run_id}/loads", response_model=list[LoadRecordRead])
def list_run_load_records(run_id: UUID, db: Session = Depends(get_db_session)) -> list:
    run = db.get(MigrationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Migration run not found")
    return LoadRecordService(db).list_for_run(run_id)


@router.get("/runs/{run_id}/loads/summary", response_model=LoadSummaryRead)
def get_run_load_summary(run_id: UUID, db: Session = Depends(get_db_session)) -> dict[str, int]:
    run = db.get(MigrationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Migration run not found")
    return LoadRecordService(db).summary_for_run(run_id)


@router.get("/projects/{project_id}/loads", response_model=list[LoadRecordRead])
def list_project_load_records(
    project_id: UUID,
    limit: int = 200,
    db: Session = Depends(get_db_session),
) -> list:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return LoadRecordService(db).list_for_project(project_id, limit=limit)


def _load_run(db: Session, run_id: UUID) -> MigrationRun | None:
    stmt = (
        select(MigrationRun)
        .where(MigrationRun.id == run_id)
        .options(selectinload(MigrationRun.batches))
    )
    return db.scalar(stmt)
