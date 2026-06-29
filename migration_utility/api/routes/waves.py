from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from migration_utility.api.deps import get_db_session
from migration_utility.datastore.models import MigrationWavePlan, Project
from migration_utility.waves.service import WaveGateError, WaveOrchestratorService

router = APIRouter(tags=["waves"])


class WavePlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    wave_count: int = Field(..., ge=1, le=100)
    accounts_per_wave: int = Field(..., ge=1, le=100_000)
    entity: str = "account"
    require_health_gate: bool | None = None
    min_cohort_score: float | None = Field(default=None, ge=0, le=100)
    max_blocked_pct: float | None = Field(default=None, ge=0, le=100)
    max_failure_pct: float | None = Field(default=None, ge=0, le=100)
    run_config: dict = Field(default_factory=dict)


class WavePlanRead(BaseModel):
    id: UUID
    name: str
    status: str
    total_waves: int
    waves_queued: int
    waves_completed: int
    waves_failed: int
    pause_reason: str | None
    plan_config: dict

    model_config = {"from_attributes": True}


@router.post(
    "/projects/{project_id}/waves",
    response_model=WavePlanRead,
    status_code=status.HTTP_201_CREATED,
)
def schedule_wave_plan(
    project_id: UUID,
    body: WavePlanCreate,
    db: Session = Depends(get_db_session),
) -> MigrationWavePlan:
    """Schedule N queued migration runs (daily wave programme)."""
    project = _get_project(project_id, db)
    svc = WaveOrchestratorService(db)
    try:
        plan = svc.create_plan(
            project,
            name=body.name,
            wave_count=body.wave_count,
            accounts_per_wave=body.accounts_per_wave,
            entity=body.entity,
            require_health_gate=body.require_health_gate,
            min_cohort_score=body.min_cohort_score,
            max_blocked_pct=body.max_blocked_pct,
            max_failure_pct=body.max_failure_pct,
            run_config=body.run_config,
        )
    except WaveGateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    db.commit()
    db.refresh(plan)
    return plan


@router.get("/projects/{project_id}/waves", response_model=list[WavePlanRead])
def list_wave_plans(project_id: UUID, db: Session = Depends(get_db_session)) -> list:
    _get_project(project_id, db)
    return WaveOrchestratorService(db).list_plans(project_id)


@router.get("/projects/{project_id}/waves/{plan_id}")
def get_wave_plan_status(
    project_id: UUID,
    plan_id: UUID,
    db: Session = Depends(get_db_session),
) -> dict:
    _get_project(project_id, db)
    plan = WaveOrchestratorService(db).get_plan(project_id, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Wave plan not found")
    return WaveOrchestratorService(db).plan_status(plan)


@router.post("/projects/{project_id}/waves/{plan_id}/pause", response_model=WavePlanRead)
def pause_wave_plan(
    project_id: UUID,
    plan_id: UUID,
    db: Session = Depends(get_db_session),
) -> MigrationWavePlan:
    _get_project(project_id, db)
    svc = WaveOrchestratorService(db)
    plan = svc.get_plan(project_id, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Wave plan not found")
    plan = svc.pause_plan(plan, reason="Paused by operator")
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/projects/{project_id}/waves/{plan_id}/resume", response_model=WavePlanRead)
def resume_wave_plan(
    project_id: UUID,
    plan_id: UUID,
    db: Session = Depends(get_db_session),
) -> MigrationWavePlan:
    _get_project(project_id, db)
    svc = WaveOrchestratorService(db)
    plan = svc.get_plan(project_id, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Wave plan not found")
    try:
        plan = svc.resume_plan(plan)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(plan)
    return plan


def _get_project(project_id: UUID, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
