from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from migration_utility.api.deps import get_db_session
from migration_utility.api.routes.rules import _get_project
from migration_utility.api.schemas import (
    MappingApprovalRead,
    TariffLoadResult,
    TariffMappingCreate,
    TariffMappingRead,
    TariffMappingSetCreate,
    TariffMappingSetRead,
    WorkflowTransition,
)
from migration_utility.tariff.service import TariffMappingService
from migration_utility.workflow import MappingEntityType, MappingRole, MappingWorkflowState
from migration_utility.workflow.service import WorkflowService

router = APIRouter(prefix="/projects/{project_id}/tariffs", tags=["tariffs"])


def _get_tariff_set(project_id: UUID, tariff_set_id: UUID, db: Session):
    tariff_set = TariffMappingService(db).get_set(project_id, tariff_set_id)
    if not tariff_set:
        raise HTTPException(status_code=404, detail="Tariff mapping set not found")
    return tariff_set


@router.get("", response_model=list[TariffMappingSetRead])
def list_tariff_sets(project_id: UUID, db: Session = Depends(get_db_session)):
    _get_project(project_id, db)
    return TariffMappingService(db).list_sets(project_id)


@router.post("", response_model=TariffMappingSetRead, status_code=status.HTTP_201_CREATED)
def create_tariff_set(
    project_id: UUID, body: TariffMappingSetCreate, db: Session = Depends(get_db_session)
):
    project = _get_project(project_id, db)
    return TariffMappingService(db).create_set(
        project, name=body.name, description=body.description
    )


@router.post("/seed", response_model=TariffMappingSetRead)
def seed_tariff_mappings(project_id: UUID, db: Session = Depends(get_db_session)):
    project = _get_project(project_id, db)
    return TariffMappingService(db).seed_defaults(project)


@router.post("/{tariff_set_id}/mappings", response_model=TariffMappingRead, status_code=201)
def add_tariff_mapping(
    project_id: UUID,
    tariff_set_id: UUID,
    body: TariffMappingCreate,
    db: Session = Depends(get_db_session),
):
    tariff_set = _get_tariff_set(project_id, tariff_set_id, db)
    try:
        return TariffMappingService(db).add_mapping(
            tariff_set,
            source_code=body.source_code,
            target_code=body.target_code,
            description=body.description,
            config=body.config,
            sort_order=body.sort_order,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{tariff_set_id}/workflow", response_model=TariffMappingSetRead)
def transition_tariff_workflow(
    project_id: UUID,
    tariff_set_id: UUID,
    body: WorkflowTransition,
    db: Session = Depends(get_db_session),
):
    project = _get_project(project_id, db)
    tariff_set = _get_tariff_set(project_id, tariff_set_id, db)
    try:
        state = MappingWorkflowState(body.workflow_state)
        role = MappingRole(body.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        return TariffMappingService(db).transition(
            project,
            tariff_set,
            target_state=state,
            actor=body.actor,
            role=role,
            comment=body.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{tariff_set_id}/approvals", response_model=list[MappingApprovalRead])
def list_tariff_approvals(
    project_id: UUID, tariff_set_id: UUID, db: Session = Depends(get_db_session)
):
    _get_project(project_id, db)
    _get_tariff_set(project_id, tariff_set_id, db)
    return WorkflowService(db).list_approvals(
        project_id, MappingEntityType.TARIFF_SET, tariff_set_id
    )


@router.post("/{tariff_set_id}/load", response_model=TariffLoadResult)
def load_tariffs_to_target(
    project_id: UUID, tariff_set_id: UUID, db: Session = Depends(get_db_session)
):
    project = _get_project(project_id, db)
    tariff_set = _get_tariff_set(project_id, tariff_set_id, db)
    try:
        result = TariffMappingService(db).load_signed_off(project, tariff_set)
        return TariffLoadResult(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
