from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from migration_utility.api.deps import get_db_session, get_schema_registry, get_target_registry
from migration_utility.api.routes.rules import _get_project, _get_rule_set
from migration_utility.api.schemas import MappingApprovalRead, MappingMatrixRead, MappingMatrixUpdate
from migration_utility.mapping.service import MappingMatrixService
from migration_utility.rules.service import RuleSetService
from migration_utility.schema.registry import SchemaRegistry
from migration_utility.schema.target_registry import TargetSchemaRegistry
from migration_utility.workflow import MappingEntityType, MappingRole
from migration_utility.workflow.service import WorkflowService

router = APIRouter(prefix="/projects/{project_id}/mapping", tags=["mapping"])


@router.get("/rules/{rule_set_id}/matrix", response_model=MappingMatrixRead)
def get_mapping_matrix(
    project_id: UUID,
    rule_set_id: UUID,
    db: Session = Depends(get_db_session),
    source_registry: SchemaRegistry = Depends(get_schema_registry),
    target_registry: TargetSchemaRegistry = Depends(get_target_registry),
):
    project = _get_project(project_id, db)
    rule_set = _get_rule_set(project_id, rule_set_id, db)
    return MappingMatrixService(db, source_registry, target_registry).get_matrix(project, rule_set)


@router.put("/rules/{rule_set_id}/matrix", response_model=MappingMatrixRead)
def update_mapping_matrix(
    project_id: UUID,
    rule_set_id: UUID,
    body: MappingMatrixUpdate,
    db: Session = Depends(get_db_session),
    source_registry: SchemaRegistry = Depends(get_schema_registry),
    target_registry: TargetSchemaRegistry = Depends(get_target_registry),
):
    project = _get_project(project_id, db)
    rule_set = _get_rule_set(project_id, rule_set_id, db)
    service = MappingMatrixService(db, source_registry, target_registry)
    try:
        rule_set = service.upsert_mappings(rule_set, body.rows)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    rule_set = _get_rule_set(project_id, rule_set_id, db)
    return service.get_matrix(project, rule_set)


@router.get("/rules/{rule_set_id}/approvals", response_model=list[MappingApprovalRead])
def list_rule_set_approvals(
    project_id: UUID, rule_set_id: UUID, db: Session = Depends(get_db_session)
):
    _get_project(project_id, db)
    _get_rule_set(project_id, rule_set_id, db)
    return WorkflowService(db).list_approvals(
        project_id, MappingEntityType.RULE_SET, rule_set_id
    )


@router.get("/rules/{rule_set_id}/workflow/options")
def workflow_options(
    project_id: UUID,
    rule_set_id: UUID,
    role: str = "mapping_lead",
    db: Session = Depends(get_db_session),
):
    rule_set = _get_rule_set(project_id, rule_set_id, db)
    try:
        mapping_role = MappingRole(role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid role: {role!r}") from exc
    return {
        "current_state": rule_set.workflow_state,
        "allowed_transitions": WorkflowService(db).allowed_transitions(
            rule_set.workflow_state, mapping_role
        ),
    }
