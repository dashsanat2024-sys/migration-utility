from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from migration_utility.datastore.models import FieldMapping, RuleSet, ValidationRule
from migration_utility.rules.types import FieldMappingDef, LoadedRuleSet, ValidationRuleDef
from migration_utility.workflow import MappingWorkflowState


class RuleLoader:
    """Load rule sets from the database for pipeline execution."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def load_for_run(
        self,
        project_id: UUID,
        entity: str,
        *,
        rule_set_id: UUID | None = None,
        require_approved: bool = True,
    ) -> LoadedRuleSet | None:
        if rule_set_id:
            rule_set = self._get_with_rules(rule_set_id)
            if rule_set is None or rule_set.project_id != project_id:
                return None
        else:
            rule_set = self._get_latest_approved(project_id, entity)
            if rule_set is None:
                return None

        loaded = self._to_loaded(rule_set)
        if require_approved and not loaded.is_runnable:
            raise ValueError(
                f"Rule set {loaded.name!r} v{loaded.version} is {loaded.workflow_state!r} — approval required"
            )
        return loaded

    def list_for_project(self, project_id: UUID, entity: str | None = None) -> list[RuleSet]:
        stmt = select(RuleSet).where(RuleSet.project_id == project_id)
        if entity:
            stmt = stmt.where(RuleSet.entity == entity)
        stmt = stmt.options(
            selectinload(RuleSet.validation_rules),
            selectinload(RuleSet.field_mappings),
        ).order_by(RuleSet.entity, RuleSet.version.desc())
        return list(self._db.scalars(stmt))

    def _get_with_rules(self, rule_set_id: UUID) -> RuleSet | None:
        stmt = (
            select(RuleSet)
            .where(RuleSet.id == rule_set_id)
            .options(
                selectinload(RuleSet.validation_rules),
                selectinload(RuleSet.field_mappings),
            )
        )
        return self._db.scalar(stmt)

    def _get_latest_approved(self, project_id: UUID, entity: str) -> RuleSet | None:
        stmt = (
            select(RuleSet)
            .where(
                RuleSet.project_id == project_id,
                RuleSet.entity == entity,
                RuleSet.workflow_state.in_(
                    [MappingWorkflowState.APPROVED.value, MappingWorkflowState.SIGNED_OFF.value]
                ),
            )
            .options(
                selectinload(RuleSet.validation_rules),
                selectinload(RuleSet.field_mappings),
            )
            .order_by(RuleSet.version.desc())
            .limit(1)
        )
        return self._db.scalar(stmt)

    @staticmethod
    def _to_loaded(rule_set: RuleSet) -> LoadedRuleSet:
        return LoadedRuleSet(
            id=str(rule_set.id),
            project_id=str(rule_set.project_id),
            entity=rule_set.entity,
            name=rule_set.name,
            version=rule_set.version,
            workflow_state=rule_set.workflow_state,
            validation_rules=[
                ValidationRuleDef(
                    id=str(r.id),
                    name=r.name,
                    rule_type=r.rule_type,
                    field_name=r.field_name,
                    config=r.config or {},
                    enabled=r.enabled,
                )
                for r in sorted(rule_set.validation_rules, key=lambda x: x.sort_order)
            ],
            field_mappings=[
                FieldMappingDef(
                    id=str(m.id),
                    source_field=m.source_field,
                    target_field=m.target_field,
                    transform_type=m.transform_type,
                    config=m.config or {},
                    enabled=m.enabled,
                    sort_order=m.sort_order,
                )
                for m in sorted(rule_set.field_mappings, key=lambda x: x.sort_order)
            ],
        )
