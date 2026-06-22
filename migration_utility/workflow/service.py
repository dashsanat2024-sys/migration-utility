from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.core.enums import AuditAction
from migration_utility.datastore.models import MappingApproval, Project
from migration_utility.services.audit import write_audit
from migration_utility.workflow import MappingEntityType, MappingRole, MappingWorkflowState
from migration_utility.workflow.engine import WorkflowEngine


class WorkflowService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._engine = WorkflowEngine()

    def transition(
        self,
        project: Project,
        *,
        entity_type: MappingEntityType,
        entity_id: UUID,
        current_state: str,
        target_state: MappingWorkflowState,
        actor: str,
        role: MappingRole,
        comment: str | None = None,
    ) -> MappingWorkflowState:
        current = MappingWorkflowState(current_state)
        self._engine.validate(current, target_state, role)

        approval = MappingApproval(
            project_id=project.id,
            entity_type=entity_type.value,
            entity_id=entity_id,
            from_state=current.value,
            to_state=target_state.value,
            actor=actor,
            role=role.value,
            comment=comment,
        )
        self._db.add(approval)
        write_audit(
            self._db,
            entity_type=entity_type.value,
            entity_id=str(entity_id),
            action=AuditAction.STATUS_CHANGED,
            message=f"{current.value} → {target_state.value} by {actor} ({role.value})",
            details={"comment": comment},
            project_id=project.id,
            actor=actor,
        )
        return target_state

    def list_approvals(
        self,
        project_id: UUID,
        entity_type: MappingEntityType,
        entity_id: UUID,
    ) -> list[MappingApproval]:
        stmt = (
            select(MappingApproval)
            .where(
                MappingApproval.project_id == project_id,
                MappingApproval.entity_type == entity_type.value,
                MappingApproval.entity_id == entity_id,
            )
            .order_by(MappingApproval.created_at.asc())
        )
        return list(self._db.scalars(stmt))

    def allowed_transitions(self, current_state: str, role: MappingRole) -> list[str]:
        return self._engine.next_states(MappingWorkflowState(current_state), role)
