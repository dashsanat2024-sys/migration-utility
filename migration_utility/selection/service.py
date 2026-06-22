from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from migration_utility.core.enums import AuditAction, CandidateStatus
from migration_utility.datastore.models import (
    Batch,
    Candidate,
    Project,
    SelectionCriterion,
    SelectionProfile,
)
from migration_utility.datastore.session import get_engine
from migration_utility.ingest.staging import (
    fetch_staged_rows,
    staging_table_name,
    tag_staging_rows,
)
from migration_utility.selection.engine import SelectionEngine
from migration_utility.selection.loader import SelectionLoader
from migration_utility.selection.types import LoadedSelectionProfile, SelectionLogic, SelectionOperator
from migration_utility.services.audit import write_audit


class SelectionProfileService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_profile(
        self,
        project: Project,
        *,
        entity: str,
        name: str,
        description: str | None = None,
        logic: str = SelectionLogic.AND.value,
        max_candidates: int | None = None,
        is_default: bool = False,
    ) -> SelectionProfile:
        if is_default:
            self._clear_default(project.id, entity)
        profile = SelectionProfile(
            project_id=project.id,
            entity=entity,
            name=name,
            description=description,
            logic=logic,
            max_candidates=max_candidates,
            is_default=is_default,
        )
        self._db.add(profile)
        self._db.flush()
        write_audit(
            self._db,
            entity_type="selection_profile",
            entity_id=str(profile.id),
            action=AuditAction.CREATED,
            message=f"Selection profile {name} created",
            project_id=project.id,
        )
        self._db.commit()
        self._db.refresh(profile)
        return profile

    def add_criterion(
        self,
        profile: SelectionProfile,
        *,
        field_name: str,
        operator: str,
        value: Any = None,
        label: str | None = None,
        sort_order: int = 0,
        enabled: bool = True,
    ) -> SelectionCriterion:
        criterion = SelectionCriterion(
            profile_id=profile.id,
            field_name=field_name,
            operator=operator,
            value=value,
            label=label,
            sort_order=sort_order,
            enabled=enabled,
        )
        self._db.add(criterion)
        self._db.commit()
        self._db.refresh(criterion)
        return criterion

    def toggle_criterion(
        self, profile_id: UUID, criterion_id: UUID, *, enabled: bool
    ) -> SelectionCriterion:
        criterion = self._db.get(SelectionCriterion, criterion_id)
        if not criterion or criterion.profile_id != profile_id:
            raise ValueError("Criterion not found")
        criterion.enabled = enabled
        self._db.commit()
        self._db.refresh(criterion)
        return criterion

    def seed_account_defaults(self, project: Project) -> SelectionProfile:
        existing = self._db.scalar(
            select(SelectionProfile).where(
                SelectionProfile.project_id == project.id,
                SelectionProfile.entity == "account",
                SelectionProfile.name == "Active Accounts",
            )
        )
        if existing:
            return existing

        profile = self.create_profile(
            project,
            entity="account",
            name="Active Accounts",
            description="Default account selection — active status only",
            logic=SelectionLogic.AND.value,
            max_candidates=1000,
            is_default=True,
        )
        self.add_criterion(
            profile,
            field_name="status",
            operator=SelectionOperator.EQ.value,
            value="active",
            label="Status is active",
            sort_order=1,
        )
        return profile

    def _clear_default(self, project_id: UUID, entity: str) -> None:
        for profile in self._db.scalars(
            select(SelectionProfile).where(
                SelectionProfile.project_id == project_id,
                SelectionProfile.entity == entity,
                SelectionProfile.is_default.is_(True),
            )
        ):
            profile.is_default = False


class CandidateService:
    """Selects candidates from staging and binds them to migration batches."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._engine = SelectionEngine()
        self._loader = SelectionLoader(db)

    def preview(
        self,
        project: Project,
        entity: str,
        *,
        profile_id: UUID | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        profile = self._resolve_profile(project.id, entity, profile_id)
        rows = _dedupe_by_external_id(self._fetch_available(project, entity))
        selected, excluded = self._apply_profile(rows, profile, limit=limit)
        return {
            "profile_id": str(profile.id),
            "profile_name": profile.name,
            "total_available": len(rows),
            "selected_count": len(selected),
            "excluded_count": len(excluded),
            "sample": selected[:5],
        }

    def populate_batch(
        self,
        project: Project,
        batch: Batch,
        entity: str,
        *,
        profile_id: UUID | None = None,
        limit: int | None = None,
    ) -> int:
        profile = self._resolve_profile(project.id, entity, profile_id)
        rows = _dedupe_by_external_id(self._fetch_available(project, entity))
        batch_limit = limit or batch.batch_config.get("limit") or profile.max_candidates
        selected, _ = self._apply_profile(rows, profile, limit=batch_limit)

        if not selected:
            return 0

        row_ids = [UUID(str(r["_row_id"])) for r in selected]
        tag_staging_rows(
            get_engine(),
            staging_table_name(project.slug, entity),
            row_ids=row_ids,
            batch_id=batch.id,
            run_id=batch.run_id,
        )

        existing = {
            c.external_id
            for c in self._db.scalars(
                select(Candidate.external_id).where(Candidate.batch_id == batch.id)
            )
        }
        created = 0
        for row in selected:
            external_id = _external_id(row)
            if external_id in existing:
                continue
            existing.add(external_id)
            candidate = Candidate(
                batch_id=batch.id,
                external_id=external_id,
                status=CandidateStatus.SELECTED.value,
                payload=_strip_meta(row),
                status_history=[
                    {"status": CandidateStatus.SELECTED.value, "message": "Selected by profile"}
                ],
            )
            batch.candidates.append(candidate)
            created += 1

        batch.batch_config = {
            **batch.batch_config,
            "selection_profile_id": str(profile.id),
            "candidate_count": created,
        }
        self._db.flush()
        write_audit(
            self._db,
            entity_type="batch",
            entity_id=str(batch.id),
            action=AuditAction.UPDATED,
            message=f"Populated {created} candidate(s) from {profile.name}",
            details={"profile_id": str(profile.id), "count": created},
            project_id=project.id,
            run_id=batch.run_id,
        )
        return created

    def list_for_batch(self, batch_id: UUID) -> list[Candidate]:
        stmt = (
            select(Candidate)
            .where(Candidate.batch_id == batch_id)
            .order_by(Candidate.external_id)
        )
        return list(self._db.scalars(stmt))

    def list_for_run(self, run_id: UUID) -> list[Candidate]:
        stmt = (
            select(Candidate)
            .join(Batch, Candidate.batch_id == Batch.id)
            .where(Batch.run_id == run_id)
            .order_by(Batch.batch_number, Candidate.external_id)
        )
        return list(self._db.scalars(stmt))

    def _resolve_profile(
        self, project_id: UUID, entity: str, profile_id: UUID | None
    ) -> LoadedSelectionProfile:
        loaded = self._loader.load_for_run(project_id, entity, profile_id=profile_id)
        if not loaded:
            raise ValueError("No enabled selection profile found for entity")
        return loaded

    def _fetch_available(self, project: Project, entity: str) -> list[dict[str, Any]]:
        table = staging_table_name(project.slug, entity)
        return fetch_staged_rows(
            get_engine(),
            table,
            project_id=project.id,
            status="staged",
            unassigned_only=True,
        )

    def _apply_profile(
        self,
        rows: list[dict[str, Any]],
        profile: LoadedSelectionProfile,
        *,
        limit: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        effective_limit = limit if limit is not None else profile.max_candidates
        return self._engine.apply(
            rows,
            profile.criteria,
            logic=profile.logic,
            limit=effective_limit,
        )


def _dedupe_by_external_id(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the first staged row per business key (e.g. duplicate uploads)."""
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: r.get("_row_number", 0)):
        key = _external_id(row)
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _external_id(row: dict[str, Any]) -> str:
    for key in ("id", "external_id", "account_id"):
        if row.get(key) is not None:
            return str(row[key])
    return str(row.get("_row_id", ""))


def _strip_meta(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if not str(k).startswith("_")}
