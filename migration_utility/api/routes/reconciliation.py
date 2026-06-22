from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from migration_utility.api.deps import get_db_session
from migration_utility.api.schemas import (
    ReconciliationExportRead,
    ReconciliationRunRead,
    ReconciliationSummaryRead,
)
from migration_utility.datastore.models import MigrationRun, Project
from migration_utility.reconciliation.service import ReconciliationService

router = APIRouter(tags=["reconciliation"])


def _get_project(project_id: UUID, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_run(project_id: UUID, run_id: UUID, db: Session) -> MigrationRun:
    run = db.scalar(
        select(MigrationRun)
        .where(MigrationRun.id == run_id, MigrationRun.project_id == project_id)
        .options(selectinload(MigrationRun.batches))
    )
    if not run:
        raise HTTPException(status_code=404, detail="Migration run not found")
    return run


@router.get("/projects/{project_id}/reconciliation", response_model=ReconciliationSummaryRead)
def project_reconciliation_summary(
    project_id: UUID,
    entity: str = "account",
    db: Session = Depends(get_db_session),
):
    project = _get_project(project_id, db)
    return ReconciliationService(db).project_dashboard(project, entity=entity)


@router.get("/projects/{project_id}/reconciliation/export", response_model=ReconciliationExportRead)
def export_reconciliation_dataset(
    project_id: UUID,
    entity: str = "account",
    db: Session = Depends(get_db_session),
):
    project = _get_project(project_id, db)
    return ReconciliationService(db).export_dataset(project, entity=entity)


@router.get("/runs/{run_id}/reconciliation", response_model=ReconciliationRunRead)
def run_reconciliation_report(
    run_id: UUID,
    entity: str = "account",
    db: Session = Depends(get_db_session),
):
    run = db.get(MigrationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Migration run not found")
    project = _get_project(run.project_id, db)
    run = _get_run(project.id, run_id, db)
    return ReconciliationService(db).run_report(project, run, entity=entity)


@router.get("/runs/{run_id}/reconciliation/samples")
def run_reconciliation_samples(
    run_id: UUID,
    limit: int = 10,
    db: Session = Depends(get_db_session),
):
    run = db.get(MigrationRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Migration run not found")
    return ReconciliationService(db).sample_diffs(run_id, limit=limit)


@router.get("/projects/{project_id}/reconciliation/export.json")
def download_reconciliation_export(
    project_id: UUID,
    entity: str = "account",
    db: Session = Depends(get_db_session),
):
    project = _get_project(project_id, db)
    data = ReconciliationService(db).export_dataset(project, entity=entity)
    import json

    body = json.dumps(data, indent=2, default=str)
    filename = f"reconciliation_{project.slug}_{entity}.json"
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
