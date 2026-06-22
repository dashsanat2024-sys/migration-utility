from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from migration_utility.core.enums import AuditAction
from migration_utility.datastore.models import Project, TariffMapping, TariffMappingSet
from migration_utility.services.audit import write_audit
from migration_utility.workflow import MappingEntityType, MappingRole, MappingWorkflowState
from migration_utility.workflow.service import WorkflowService


class TariffMappingService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._workflow = WorkflowService(db)

    def list_sets(self, project_id: UUID) -> list[TariffMappingSet]:
        stmt = (
            select(TariffMappingSet)
            .where(TariffMappingSet.project_id == project_id)
            .options(selectinload(TariffMappingSet.mappings))
            .order_by(TariffMappingSet.version.desc())
        )
        return list(self._db.scalars(stmt))

    def get_set(self, project_id: UUID, tariff_set_id: UUID) -> TariffMappingSet | None:
        stmt = (
            select(TariffMappingSet)
            .where(
                TariffMappingSet.id == tariff_set_id,
                TariffMappingSet.project_id == project_id,
            )
            .options(selectinload(TariffMappingSet.mappings))
        )
        return self._db.scalar(stmt)

    def create_set(self, project: Project, *, name: str, description: str | None = None) -> TariffMappingSet:
        next_version = self._db.scalar(
            select(func.coalesce(func.max(TariffMappingSet.version), 0)).where(
                TariffMappingSet.project_id == project.id
            )
        )
        tariff_set = TariffMappingSet(
            project_id=project.id,
            name=name,
            description=description,
            version=int(next_version or 0) + 1,
        )
        self._db.add(tariff_set)
        self._db.commit()
        self._db.refresh(tariff_set)
        return tariff_set

    def add_mapping(
        self,
        tariff_set: TariffMappingSet,
        *,
        source_code: str,
        target_code: str,
        description: str | None = None,
        config: dict[str, Any] | None = None,
        sort_order: int = 0,
    ) -> TariffMapping:
        if tariff_set.workflow_state not in ("draft", "in_review"):
            raise ValueError("Tariff mappings are locked after approval")
        mapping = TariffMapping(
            tariff_set_id=tariff_set.id,
            source_code=source_code,
            target_code=target_code,
            description=description,
            config=config or {},
            sort_order=sort_order,
        )
        self._db.add(mapping)
        self._db.commit()
        self._db.refresh(mapping)
        return mapping

    def transition(
        self,
        project: Project,
        tariff_set: TariffMappingSet,
        *,
        target_state: MappingWorkflowState,
        actor: str,
        role: MappingRole,
        comment: str | None = None,
    ) -> TariffMappingSet:
        new_state = self._workflow.transition(
            project,
            entity_type=MappingEntityType.TARIFF_SET,
            entity_id=tariff_set.id,
            current_state=tariff_set.workflow_state,
            target_state=target_state,
            actor=actor,
            role=role,
            comment=comment,
        )
        tariff_set.workflow_state = new_state.value
        self._db.commit()
        self._db.refresh(tariff_set)
        return tariff_set

    def seed_defaults(self, project: Project) -> TariffMappingSet:
        existing = self._db.scalar(
            select(TariffMappingSet).where(
                TariffMappingSet.project_id == project.id,
                TariffMappingSet.name == "Standard Tariffs",
            )
        )
        if existing:
            return existing

        tariff_set = self.create_set(project, name="Standard Tariffs", description="Starter tariff map")
        defaults = [
            ("DOM-STD", "KRK-DOM-STD", "Domestic standard"),
            ("DOM-ECO", "KRK-DOM-ECO", "Domestic economy"),
            ("BUS-STD", "KRK-BUS-STD", "Business standard"),
        ]
        for i, (src, tgt, desc) in enumerate(defaults, start=1):
            self.add_mapping(tariff_set, source_code=src, target_code=tgt, description=desc, sort_order=i)
        return tariff_set

    def load_signed_off(self, project: Project, tariff_set: TariffMappingSet) -> dict[str, Any]:
        if tariff_set.workflow_state != MappingWorkflowState.SIGNED_OFF.value:
            raise ValueError("Only signed-off tariff sets can be loaded to target")
        from migration_utility.connectors.kraken import KrakenProductImportAdapter

        adapter = KrakenProductImportAdapter()
        records = [
            {"sourceCode": m.source_code, "productCode": m.target_code, "displayName": m.description or m.target_code}
            for m in sorted(tariff_set.mappings, key=lambda x: x.sort_order)
            if m.enabled
        ]
        loaded, failed = adapter.import_products(records, project_id=str(project.id))
        tariff_set.loaded_at = datetime.now(timezone.utc)
        write_audit(
            self._db,
            entity_type="tariff_set",
            entity_id=str(tariff_set.id),
            action=AuditAction.UPDATED,
            message=f"Loaded {len(loaded)} tariff(s) to target",
            project_id=project.id,
        )
        self._db.commit()
        self._db.refresh(tariff_set)
        return {"loaded": len(loaded), "failed": len(failed), "records": loaded}
