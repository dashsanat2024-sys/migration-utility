from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from migration_utility.core.enums import AuditAction
from migration_utility.datastore.models import FieldMapping, Project, RuleSet, ValidationRule
from migration_utility.services.audit import write_audit
from migration_utility.workflow import MappingEntityType, MappingRole, MappingWorkflowState
from migration_utility.workflow.service import WorkflowService


class RuleSetService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_rule_set(
        self,
        project: Project,
        *,
        entity: str,
        name: str,
        description: str | None = None,
    ) -> RuleSet:
        next_version = self._db.scalar(
            select(func.coalesce(func.max(RuleSet.version), 0)).where(
                RuleSet.project_id == project.id,
                RuleSet.entity == entity,
            )
        )
        rule_set = RuleSet(
            project_id=project.id,
            entity=entity,
            name=name,
            description=description,
            version=int(next_version or 0) + 1,
            workflow_state=MappingWorkflowState.DRAFT.value,
        )
        self._db.add(rule_set)
        self._db.flush()
        write_audit(
            self._db,
            entity_type="rule_set",
            entity_id=str(rule_set.id),
            action=AuditAction.CREATED,
            message=f"Rule set {name} v{rule_set.version} created",
            project_id=project.id,
        )
        self._db.commit()
        self._db.refresh(rule_set)
        return rule_set

    def add_validation_rule(
        self,
        rule_set: RuleSet,
        *,
        name: str,
        rule_type: str,
        field_name: str | None = None,
        config: dict | None = None,
        sort_order: int = 0,
    ) -> ValidationRule:
        rule = ValidationRule(
            rule_set_id=rule_set.id,
            name=name,
            rule_type=rule_type,
            field_name=field_name,
            config=config or {},
            sort_order=sort_order,
        )
        self._db.add(rule)
        self._db.commit()
        self._db.refresh(rule)
        return rule

    def add_field_mapping(
        self,
        rule_set: RuleSet,
        *,
        source_field: str | None,
        target_field: str,
        transform_type: str = "copy",
        config: dict | None = None,
        sort_order: int = 0,
    ) -> FieldMapping:
        mapping = FieldMapping(
            rule_set_id=rule_set.id,
            source_field=source_field,
            target_field=target_field,
            transform_type=transform_type,
            config=config or {},
            sort_order=sort_order,
        )
        self._db.add(mapping)
        self._db.commit()
        self._db.refresh(mapping)
        return mapping

    def transition(
        self,
        rule_set: RuleSet,
        new_state: MappingWorkflowState,
        *,
        project: Project,
        actor: str = "system",
        role: MappingRole = MappingRole.MAPPING_LEAD,
        comment: str | None = None,
    ) -> RuleSet:
        workflow = WorkflowService(self._db)
        state = workflow.transition(
            project,
            entity_type=MappingEntityType.RULE_SET,
            entity_id=rule_set.id,
            current_state=rule_set.workflow_state,
            target_state=new_state,
            actor=actor,
            role=role,
            comment=comment,
        )
        rule_set.workflow_state = state.value
        self._db.commit()
        self._db.refresh(rule_set)
        return rule_set

    def seed_account_defaults(self, project: Project) -> RuleSet:
        """Create a starter approved rule set for the account entity."""
        rule_set = self.create_rule_set(
            project, entity="account", name="Default Account Rules"
        )
        self.add_validation_rule(
            rule_set,
            name="Account ID format",
            rule_type="format",
            field_name="id",
            config={"pattern": r"^ACC-\d+$"},
            sort_order=1,
        )
        self.add_validation_rule(
            rule_set,
            name="Status values",
            rule_type="in_list",
            field_name="status",
            config={"values": ["active", "inactive"]},
            sort_order=2,
        )
        self.add_validation_rule(
            rule_set,
            name="Unique account ID",
            rule_type="unique",
            field_name="id",
            sort_order=3,
        )
        self.add_field_mapping(rule_set, source_field="id", target_field="accountId", transform_type="copy", sort_order=1)
        self.add_field_mapping(rule_set, source_field="name", target_field="accountName", transform_type="copy", sort_order=2)
        self.add_field_mapping(
            rule_set,
            source_field="status",
            target_field="accountStatus",
            transform_type="lookup",
            config={"map": {"active": "ACTIVE", "inactive": "INACTIVE"}},
            sort_order=3,
        )
        self.transition(
            rule_set,
            MappingWorkflowState.IN_REVIEW,
            project=project,
            actor="seed",
            role=MappingRole.MAPPING_LEAD,
            comment="Auto-submitted by seed",
        )
        self.transition(
            rule_set,
            MappingWorkflowState.APPROVED,
            project=project,
            actor="seed",
            role=MappingRole.BUSINESS_ANALYST,
            comment="Auto-approved by seed",
        )
        return rule_set
