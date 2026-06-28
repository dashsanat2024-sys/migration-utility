from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from migration_utility.account_health.service import AccountHealthService
from migration_utility.account_health.testing_plan import build_testing_plan
from migration_utility.api.deps import get_db_session
from migration_utility.datastore.models import AccountHealthAssessment, AccountHealthRecord, Project
from migration_utility.fallout.service import FalloutService

router = APIRouter(tags=["account-health"])


class AssessmentRead(BaseModel):
    id: UUID
    project_id: UUID
    entity: str
    row_count: int
    cohort_readiness_score: float
    summary: dict

    model_config = {"from_attributes": True}


class HealthRecordRead(BaseModel):
    id: UUID
    external_id: str
    row_number: int | None
    readiness_score: int
    readiness_status: str
    findings: list
    has_blocker: bool

    model_config = {"from_attributes": True}


class AssessRequest(BaseModel):
    entity: str = "account"
    limit: int | None = Field(default=None, ge=1, le=100_000)


@router.post("/projects/{project_id}/account-health/assess", response_model=AssessmentRead)
def run_account_health_assessment(
    project_id: UUID,
    body: AssessRequest,
    db: Session = Depends(get_db_session),
) -> AccountHealthAssessment:
    project = _get_project(project_id, db)
    svc = AccountHealthService(db)
    assessment = svc.assess_project(project, entity=body.entity, limit=body.limit)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/projects/{project_id}/account-health/latest", response_model=AssessmentRead | None)
def latest_account_health(
    project_id: UUID,
    entity: str = "account",
    db: Session = Depends(get_db_session),
) -> AccountHealthAssessment | None:
    _get_project(project_id, db)
    return AccountHealthService(db).latest_assessment(project_id, entity=entity)


@router.get(
    "/projects/{project_id}/account-health/{assessment_id}/records",
    response_model=list[HealthRecordRead],
)
def list_health_records(
    project_id: UUID,
    assessment_id: UUID,
    status: str | None = None,
    limit: int = 500,
    db: Session = Depends(get_db_session),
) -> list[AccountHealthRecord]:
    _get_project(project_id, db)
    assessment = db.get(AccountHealthAssessment, assessment_id)
    if not assessment or assessment.project_id != project_id:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return AccountHealthService(db).list_records(assessment_id, status=status, limit=limit)


@router.post("/projects/{project_id}/account-health/{assessment_id}/sync-fallout")
def sync_fallout_from_assessment(
    project_id: UUID,
    assessment_id: UUID,
    entity: str = "account",
    db: Session = Depends(get_db_session),
) -> dict:
    _get_project(project_id, db)
    assessment = db.get(AccountHealthAssessment, assessment_id)
    if not assessment or assessment.project_id != project_id:
        raise HTTPException(status_code=404, detail="Assessment not found")
    items = FalloutService(db).sync_assessment_fallout(
        project_id, assessment_id, entity=entity
    )
    return {"synced": len(items), "exception_ids": [str(i.id) for i in items]}


@router.get("/projects/{project_id}/migration-testing/plan")
def migration_testing_plan(
    project_id: UUID,
    db: Session = Depends(get_db_session),
) -> dict:
    project = _get_project(project_id, db)
    return build_testing_plan(target_system=project.target_system or "kraken")


def _get_project(project_id: UUID, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
