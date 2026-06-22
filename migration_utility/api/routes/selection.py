from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from migration_utility.api.deps import get_db_session
from migration_utility.api.schemas import (
    CriterionToggle,
    SelectionCriterionCreate,
    SelectionCriterionRead,
    SelectionPreviewRead,
    SelectionPreviewRequest,
    SelectionProfileCreate,
    SelectionProfileRead,
)
from migration_utility.datastore.models import Project, SelectionProfile
from migration_utility.selection.loader import SelectionLoader
from migration_utility.selection.service import CandidateService, SelectionProfileService

router = APIRouter(prefix="/projects/{project_id}/selection", tags=["selection"])


def _get_project(project_id: UUID, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_profile(project_id: UUID, profile_id: UUID, db: Session) -> SelectionProfile:
    profile = SelectionLoader(db).get_profile(project_id, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Selection profile not found")
    return profile


@router.get("/profiles", response_model=list[SelectionProfileRead])
def list_profiles(
    project_id: UUID, entity: str | None = None, db: Session = Depends(get_db_session)
) -> list[SelectionProfile]:
    _get_project(project_id, db)
    return SelectionLoader(db).list_for_project(project_id, entity)


@router.post("/profiles", response_model=SelectionProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(
    project_id: UUID, body: SelectionProfileCreate, db: Session = Depends(get_db_session)
) -> SelectionProfile:
    project = _get_project(project_id, db)
    return SelectionProfileService(db).create_profile(
        project,
        entity=body.entity,
        name=body.name,
        description=body.description,
        logic=body.logic,
        max_candidates=body.max_candidates,
        is_default=body.is_default,
    )


@router.post("/profiles/seed-account", response_model=SelectionProfileRead)
def seed_account_profile(
    project_id: UUID, db: Session = Depends(get_db_session)
) -> SelectionProfile:
    project = _get_project(project_id, db)
    profile = SelectionProfileService(db).seed_account_defaults(project)
    return SelectionLoader(db).get_profile(project_id, profile.id)  # type: ignore[return-value]


@router.post(
    "/profiles/{profile_id}/criteria",
    response_model=SelectionCriterionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_criterion(
    project_id: UUID,
    profile_id: UUID,
    body: SelectionCriterionCreate,
    db: Session = Depends(get_db_session),
):
    profile = _get_profile(project_id, profile_id, db)
    return SelectionProfileService(db).add_criterion(
        profile,
        field_name=body.field_name,
        operator=body.operator,
        value=body.value,
        label=body.label,
        sort_order=body.sort_order,
        enabled=body.enabled,
    )


@router.patch(
    "/profiles/{profile_id}/criteria/{criterion_id}",
    response_model=SelectionCriterionRead,
)
def toggle_criterion(
    project_id: UUID,
    profile_id: UUID,
    criterion_id: UUID,
    body: CriterionToggle,
    db: Session = Depends(get_db_session),
):
    _get_profile(project_id, profile_id, db)
    try:
        return SelectionProfileService(db).toggle_criterion(
            profile_id, criterion_id, enabled=body.enabled
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/preview", response_model=SelectionPreviewRead)
def preview_selection(
    project_id: UUID,
    body: SelectionPreviewRequest,
    db: Session = Depends(get_db_session),
) -> dict:
    project = _get_project(project_id, db)
    try:
        return CandidateService(db).preview(
            project,
            body.entity,
            profile_id=body.profile_id,
            limit=body.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
