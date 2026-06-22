from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from migration_utility.datastore.models import SelectionProfile
from migration_utility.selection.types import CriterionDef, LoadedSelectionProfile


class SelectionLoader:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_project(
        self, project_id: UUID, entity: str | None = None
    ) -> list[SelectionProfile]:
        stmt = (
            select(SelectionProfile)
            .where(SelectionProfile.project_id == project_id)
            .options(selectinload(SelectionProfile.criteria))
            .order_by(SelectionProfile.is_default.desc(), SelectionProfile.name)
        )
        if entity:
            stmt = stmt.where(SelectionProfile.entity == entity)
        return list(self._db.scalars(stmt))

    def get_profile(
        self, project_id: UUID, profile_id: UUID
    ) -> SelectionProfile | None:
        stmt = (
            select(SelectionProfile)
            .where(
                SelectionProfile.id == profile_id,
                SelectionProfile.project_id == project_id,
            )
            .options(selectinload(SelectionProfile.criteria))
        )
        return self._db.scalar(stmt)

    def load_for_run(
        self,
        project_id: UUID,
        entity: str,
        *,
        profile_id: UUID | None = None,
    ) -> LoadedSelectionProfile | None:
        if profile_id:
            profile = self.get_profile(project_id, profile_id)
        else:
            profile = self._default_profile(project_id, entity)
        if not profile or not profile.enabled:
            return None
        return self._to_loaded(profile)

    def _default_profile(self, project_id: UUID, entity: str) -> SelectionProfile | None:
        stmt = (
            select(SelectionProfile)
            .where(
                SelectionProfile.project_id == project_id,
                SelectionProfile.entity == entity,
                SelectionProfile.is_default.is_(True),
                SelectionProfile.enabled.is_(True),
            )
            .options(selectinload(SelectionProfile.criteria))
        )
        return self._db.scalar(stmt)

    def _to_loaded(self, profile: SelectionProfile) -> LoadedSelectionProfile:
        return LoadedSelectionProfile(
            id=profile.id,
            name=profile.name,
            entity=profile.entity,
            logic=profile.logic,
            max_candidates=profile.max_candidates,
            criteria=[
                CriterionDef(
                    id=c.id,
                    field_name=c.field_name,
                    operator=c.operator,
                    value=c.value,
                    enabled=c.enabled,
                    sort_order=c.sort_order,
                )
                for c in sorted(profile.criteria, key=lambda x: x.sort_order)
            ],
        )
