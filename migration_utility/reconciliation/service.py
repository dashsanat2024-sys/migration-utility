from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from migration_utility.core.enums import RunStatus
from migration_utility.datastore.models import (
    Batch,
    Candidate,
    IngestError,
    LoadRecord,
    MigrationRun,
    Project,
)
from migration_utility.datastore.session import get_engine
from migration_utility.ingest.staging import count_staged_rows, staging_table_name


class ReconciliationService:
    """Aggregate staging, pipeline, and target load data for reconciliation reports."""

    def __init__(self, db: Session, engine: Engine | None = None) -> None:
        self._db = db
        self._engine = engine or get_engine()

    def project_dashboard(self, project: Project, *, entity: str = "account") -> dict[str, Any]:
        table = staging_table_name(project.slug, entity)
        staged_total = count_staged_rows(self._engine, table, project.id)

        runs = list(
            self._db.scalars(
                select(MigrationRun)
                .where(MigrationRun.project_id == project.id)
                .order_by(MigrationRun.created_at.desc())
            )
        )

        load_totals = self._db.execute(
            select(
                LoadRecord.status,
                func.count(LoadRecord.id),
            )
            .where(LoadRecord.project_id == project.id, LoadRecord.entity == entity)
            .group_by(LoadRecord.status)
        ).all()
        load_by_status = {row[0]: int(row[1]) for row in load_totals}

        open_errors = self._db.scalar(
            select(func.count(IngestError.id)).where(
                IngestError.project_id == project.id,
                IngestError.entity == entity,
                IngestError.resolved.is_(False),
            )
        ) or 0

        return {
            "project_id": str(project.id),
            "entity": entity,
            "staging_table": table,
            "counts": {
                "staged_total": staged_total,
                "ingest_errors_open": int(open_errors),
                "runs_total": len(runs),
                "runs_completed": sum(1 for r in runs if r.status == RunStatus.COMPLETED.value),
                "runs_failed": sum(1 for r in runs if r.status == RunStatus.FAILED.value),
                "loads_ok": load_by_status.get("loaded", 0),
                "loads_failed": load_by_status.get("failed", 0),
            },
            "recent_runs": [
                {
                    "run_id": str(r.id),
                    "name": r.name,
                    "status": r.status,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                }
                for r in runs[:10]
            ],
        }

    def run_report(self, project: Project, run: MigrationRun, *, entity: str = "account") -> dict[str, Any]:
        batch_ids = [b.id for b in run.batches]
        table = staging_table_name(project.slug, entity)
        staged_for_run = self._count_staged_for_batches(table, project.id, batch_ids)

        candidates = self._candidates_for_run(run.id)
        candidate_by_status: dict[str, int] = {}
        for c in candidates:
            candidate_by_status[c.status] = candidate_by_status.get(c.status, 0) + 1

        loads = list(
            self._db.scalars(select(LoadRecord).where(LoadRecord.run_id == run.id))
        )
        load_by_status: dict[str, int] = {}
        for lr in loads:
            load_by_status[lr.status] = load_by_status.get(lr.status, 0) + 1

        selected = len(candidates)
        loaded = load_by_status.get("loaded", 0)
        load_failed = load_by_status.get("failed", 0)

        funnel = {
            "staged_in_run": staged_for_run,
            "candidates_selected": selected,
            "candidates_loaded": candidate_by_status.get("loaded", 0),
            "candidates_failed": candidate_by_status.get("failed", 0),
            "target_loaded": loaded,
            "target_failed": load_failed,
        }

        variance = {
            "staged_minus_selected": staged_for_run - selected,
            "selected_minus_target_ok": selected - loaded,
            "unaccounted": selected - loaded - load_failed,
        }

        match_rate = round(loaded / selected, 4) if selected else None
        reconciliation_status = self._reconciliation_status(selected, loaded, load_failed, variance)

        stage_stats = []
        for batch in sorted(run.batches, key=lambda b: b.batch_number):
            if batch.stats and batch.stats.get("stages"):
                stage_stats.append(
                    {
                        "batch_number": batch.batch_number,
                        "batch_status": batch.status,
                        "stages": batch.stats.get("stages", []),
                        "load_summary": batch.stats.get("load_summary"),
                    }
                )

        open_errors = self._db.scalar(
            select(func.count(IngestError.id)).where(
                IngestError.project_id == project.id,
                IngestError.entity == entity,
                IngestError.resolved.is_(False),
            )
        ) or 0

        return {
            "run_id": str(run.id),
            "run_name": run.name,
            "run_status": run.status,
            "entity": entity,
            "funnel": funnel,
            "variance": variance,
            "match_rate": match_rate,
            "reconciliation_status": reconciliation_status,
            "candidate_status": candidate_by_status,
            "load_status": load_by_status,
            "ingest_errors_open": int(open_errors),
            "batch_stage_stats": stage_stats,
            "samples": self.sample_diffs(run.id, limit=5),
        }

    def sample_diffs(self, run_id: UUID, *, limit: int = 10) -> list[dict[str, Any]]:
        candidates = self._candidates_for_run(run_id)
        loads = {
            lr.external_id: lr
            for lr in self._db.scalars(select(LoadRecord).where(LoadRecord.run_id == run_id))
        }

        samples: list[dict[str, Any]] = []
        for candidate in candidates[: limit * 2]:
            load = loads.get(candidate.external_id)
            source = candidate.payload or {}
            target = (load.response_payload or load.request_payload or {}) if load else {}
            diff_fields = _diff_payloads(source, target)
            samples.append(
                {
                    "external_id": candidate.external_id,
                    "candidate_status": candidate.status,
                    "load_status": load.status if load else None,
                    "source_payload": source,
                    "target_payload": target,
                    "diff_fields": diff_fields,
                    "reconciled": load is not None and load.status == "loaded" and not diff_fields,
                }
            )
            if len(samples) >= limit:
                break
        return samples

    def export_dataset(self, project: Project, *, entity: str = "account") -> dict[str, Any]:
        dashboard = self.project_dashboard(project, entity=entity)
        runs = list(
            self._db.scalars(
                select(MigrationRun)
                .where(MigrationRun.project_id == project.id)
                .order_by(MigrationRun.created_at.desc())
            )
        )
        run_reports = []
        for run in runs:
            report = self.run_report(project, run, entity=entity)
            run_reports.append(
                {
                    "run_id": report["run_id"],
                    "run_name": report["run_name"],
                    "run_status": report["run_status"],
                    "funnel": report["funnel"],
                    "variance": report["variance"],
                    "match_rate": report["match_rate"],
                    "reconciliation_status": report["reconciliation_status"],
                }
            )

        load_rows = [
            {
                "external_id": lr.external_id,
                "status": lr.status,
                "run_id": str(lr.run_id) if lr.run_id else None,
                "target_adapter_key": lr.target_adapter_key,
                "error_message": lr.error_message,
            }
            for lr in self._db.scalars(
                select(LoadRecord)
                .where(LoadRecord.project_id == project.id, LoadRecord.entity == entity)
                .order_by(LoadRecord.created_at.desc())
                .limit(500)
            )
        ]

        return {
            "project_id": str(project.id),
            "project_slug": project.slug,
            "entity": entity,
            "generated_at": _utcnow_iso(),
            "summary": dashboard["counts"],
            "runs": run_reports,
            "load_records": load_rows,
        }

    def _candidates_for_run(self, run_id: UUID) -> list[Candidate]:
        stmt = (
            select(Candidate)
            .join(Batch, Candidate.batch_id == Batch.id)
            .where(Batch.run_id == run_id)
            .order_by(Candidate.external_id)
        )
        return list(self._db.scalars(stmt))

    def _count_staged_for_batches(
        self,
        table_name: str,
        project_id: UUID,
        batch_ids: list[UUID],
    ) -> int:
        if not batch_ids:
            return 0
        inspector = inspect(self._engine)
        if table_name not in inspector.get_table_names():
            return 0

        placeholders = ", ".join(f":b{i}" for i in range(len(batch_ids)))
        params: dict[str, Any] = {"project_id": project_id}
        for i, bid in enumerate(batch_ids):
            params[f"b{i}"] = bid

        sql = text(
            f"SELECT COUNT(*) FROM {table_name} "
            f"WHERE _project_id = :project_id AND _batch_id IN ({placeholders})"
        )
        with self._engine.connect() as conn:
            return int(conn.execute(sql, params).scalar_one())

    @staticmethod
    def _reconciliation_status(
        selected: int,
        loaded: int,
        load_failed: int,
        variance: dict[str, int],
    ) -> str:
        if selected == 0:
            return "no_candidates"
        if loaded + load_failed >= selected and variance.get("unaccounted", 0) == 0:
            return "balanced"
        if loaded > 0:
            return "partial"
        return "variance"


def _diff_payloads(source: dict[str, Any], target: dict[str, Any]) -> list[str]:
    ignore = {
        "_row_id",
        "_project_id",
        "_batch_id",
        "_run_id",
        "_source_file_id",
        "_row_number",
        "_status",
        "_ingested_at",
        "importStatus",
        "krakenAccountId",
        "environment",
        "projectId",
        "idocNumber",
        "idocType",
        "sapCustomerNumber",
        "exportPath",
    }
    diffs: list[str] = []
    keys = set(source) | set(target)
    for key in sorted(keys):
        if key in ignore or str(key).startswith("_"):
            continue
        if source.get(key) != target.get(key):
            diffs.append(key)
    return diffs


def _utcnow_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()
