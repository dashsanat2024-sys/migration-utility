from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from migration_utility.api.deps import get_db_session
from migration_utility.api.schemas import (
    FieldMappingCreate,
    FieldMappingRead,
    RuleSetCreate,
    RuleSetRead,
    TransformPreviewRead,
    TransformPreviewRequest,
    ValidationRuleCreate,
    ValidationRuleRead,
    WorkflowTransition,
)
from migration_utility.auth.deps import get_optional_user
from migration_utility.datastore.models import Project, RuleSet, User
from migration_utility.rules.engine import TransformEngine
from migration_utility.rules.loader import RuleLoader
from migration_utility.rules.service import RuleSetService
from migration_utility.rules.types import FieldMappingDef
from migration_utility.workflow import MappingRole, MappingWorkflowState

router = APIRouter(prefix="/projects/{project_id}/rules", tags=["rules"])


def _get_project(project_id: UUID, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_rule_set(project_id: UUID, rule_set_id: UUID, db: Session) -> RuleSet:
    stmt = (
        select(RuleSet)
        .where(RuleSet.id == rule_set_id, RuleSet.project_id == project_id)
        .options(selectinload(RuleSet.validation_rules), selectinload(RuleSet.field_mappings))
    )
    rule_set = db.scalar(stmt)
    if not rule_set:
        raise HTTPException(status_code=404, detail="Rule set not found")
    return rule_set


@router.get("", response_model=list[RuleSetRead])
def list_rule_sets(
    project_id: UUID, entity: str | None = None, db: Session = Depends(get_db_session)
) -> list[RuleSet]:
    _get_project(project_id, db)
    return RuleLoader(db).list_for_project(project_id, entity)


@router.post("", response_model=RuleSetRead, status_code=status.HTTP_201_CREATED)
def create_rule_set(
    project_id: UUID, body: RuleSetCreate, db: Session = Depends(get_db_session)
) -> RuleSet:
    project = _get_project(project_id, db)
    return RuleSetService(db).create_rule_set(
        project, entity=body.entity, name=body.name, description=body.description
    )


@router.post("/seed-account", response_model=RuleSetRead, status_code=status.HTTP_201_CREATED)
def seed_account_rules(project_id: UUID, db: Session = Depends(get_db_session)) -> RuleSet:
    project = _get_project(project_id, db)
    rule_set = RuleSetService(db).seed_account_defaults(project)
    return _get_rule_set(project_id, rule_set.id, db)


@router.get("/{rule_set_id}", response_model=RuleSetRead)
def get_rule_set(
    project_id: UUID, rule_set_id: UUID, db: Session = Depends(get_db_session)
) -> RuleSet:
    return _get_rule_set(project_id, rule_set_id, db)


@router.post("/{rule_set_id}/validation-rules", response_model=ValidationRuleRead, status_code=201)
def add_validation_rule(
    project_id: UUID,
    rule_set_id: UUID,
    body: ValidationRuleCreate,
    db: Session = Depends(get_db_session),
):
    rule_set = _get_rule_set(project_id, rule_set_id, db)
    return RuleSetService(db).add_validation_rule(
        rule_set,
        name=body.name,
        rule_type=body.rule_type,
        field_name=body.field_name,
        config=body.config,
        sort_order=body.sort_order,
    )


@router.post("/{rule_set_id}/field-mappings", response_model=FieldMappingRead, status_code=201)
def add_field_mapping(
    project_id: UUID,
    rule_set_id: UUID,
    body: FieldMappingCreate,
    db: Session = Depends(get_db_session),
):
    rule_set = _get_rule_set(project_id, rule_set_id, db)
    return RuleSetService(db).add_field_mapping(
        rule_set,
        source_field=body.source_field,
        target_field=body.target_field,
        transform_type=body.transform_type,
        config=body.config,
        sort_order=body.sort_order,
    )


@router.post("/{rule_set_id}/preview-transform", response_model=TransformPreviewRead)
def preview_transform(
    project_id: UUID,
    rule_set_id: UUID,
    body: TransformPreviewRequest,
    db: Session = Depends(get_db_session),
) -> TransformPreviewRead:
    rule_set = _get_rule_set(project_id, rule_set_id, db)
    if body.mappings is not None:
        mapping_defs = [
            FieldMappingDef(
                id="preview",
                source_field=m.source_field,
                target_field=m.target_field,
                transform_type=m.transform_type,
                config=m.config,
                enabled=True,
                sort_order=m.sort_order or i,
            )
            for i, m in enumerate(body.mappings, start=1)
        ]
    else:
        loaded = RuleLoader(db)._to_loaded(rule_set)
        mapping_defs = loaded.field_mappings
    transformed = TransformEngine().apply(body.records, mapping_defs)
    return TransformPreviewRead(records=transformed)


@router.post("/{rule_set_id}/workflow", response_model=RuleSetRead)
def transition_workflow(
    project_id: UUID,
    rule_set_id: UUID,
    body: WorkflowTransition,
    db: Session = Depends(get_db_session),
    user: User | None = Depends(get_optional_user),
) -> RuleSet:
    rule_set = _get_rule_set(project_id, rule_set_id, db)
    project = _get_project(project_id, db)
    try:
        state = MappingWorkflowState(body.workflow_state)
        role = MappingRole(body.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid state or role") from exc
    actor = body.actor
    if user:
        actor = user.display_name
        try:
            role = MappingRole(user.role)
        except ValueError:
            pass
    try:
        updated = RuleSetService(db).transition(
            rule_set,
            state,
            project=project,
            actor=actor,
            role=role,
            comment=body.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _get_rule_set(project_id, updated.id, db)
