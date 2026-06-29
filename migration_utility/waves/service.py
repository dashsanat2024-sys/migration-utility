"""Wave orchestration — schedule runs, health gate, auto-pause on failure rate."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.account_health.service import AccountHealthService
from migration_utility.config import get_settings
from migration_utility.core.enums import AuditAction, RunStatus
from migration_utility.datastore.models import Batch, MigrationRun, MigrationWavePlan, Project
from migration_utility.services.audit import write_audit

logger = logging.getLogger(__name__)


class WaveGateError(ValueError):
    """Cohort readiness gate blocked wave scheduling."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def run_failure_pct(run: MigrationRun) -> float:
    if run.status == RunStatus.FAILED.value:
        summary = run.result_summary or {}
        if "failure_pct" in summary:
            return float(summary["failure_pct"])
        return 100.0

    loaded = failed = 0
    for batch in run.batches:
        load_summary = (batch.stats or {}).get("load_summary") or {}
        loaded += int(load_summary.get("loaded", 0))
        failed += int(load_summary.get("failed", 0))
    total = loaded + failed
    return (100.0 * failed / total) if total else 0.0


class WaveOrchestratorService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_plan(
        self,
        project: Project,
        *,
        name: str,
        wave_count: int,
        accounts_per_wave: int,
        entity: str = "account",
        require_health_gate: bool | None = None,
        min_cohort_score: float | None = None,
        max_blocked_pct: float | None = None,
        max_failure_pct: float | None = None,
        run_config: dict[str, Any] | None = None,
    ) -> MigrationWavePlan:
        settings = get_settings()
        if wave_count < 1:
            raise ValueError("wave_count must be at least 1")
        if accounts_per_wave < 1:
            raise ValueError("accounts_per_wave must be at least 1")

        gate_required = (
            require_health_gate
            if require_health_gate is not None
            else settings.wave_require_health_gate
        )
        if gate_required:
            self._check_health_gate(
                project,
                entity=entity,
                min_cohort_score=min_cohort_score or settings.wave_default_min_cohort_score,
                max_blocked_pct=max_blocked_pct or settings.wave_default_max_blocked_pct,
            )

        plan_config = {
            "entity": entity,
            "accounts_per_wave": accounts_per_wave,
            "max_failure_pct": max_failure_pct or settings.wave_default_max_failure_pct,
            "require_health_gate": gate_required,
            "min_cohort_score": min_cohort_score or settings.wave_default_min_cohort_score,
            "max_blocked_pct": max_blocked_pct or settings.wave_default_max_blocked_pct,
            "run_config": run_config or {},
        }
        plan = MigrationWavePlan(
            project_id=project.id,
            name=name,
            status="active",
            plan_config=plan_config,
            total_waves=wave_count,
            waves_queued=0,
        )
        self._db.add(plan)
        self._db.flush()

        base_run_config = {
            **(run_config or {}),
            "entity": entity,
            "async": True,
            "use_selection": plan_config["run_config"].get("use_selection", True),
            "candidate_limit": accounts_per_wave,
            "wave_plan_id": str(plan.id),
        }

        for wave_number in range(1, wave_count + 1):
            self._queue_wave_run(
                project,
                plan,
                wave_number=wave_number,
                run_config={**base_run_config, "wave_number": wave_number},
            )

        plan.waves_queued = wave_count
        write_audit(
            self._db,
            entity_type="migration_wave_plan",
            entity_id=str(plan.id),
            action=AuditAction.CREATED,
            message=f"Wave plan {name} scheduled {wave_count} run(s)",
            details={
                "total_waves": wave_count,
                "accounts_per_wave": accounts_per_wave,
                "daily_capacity": wave_count * accounts_per_wave,
            },
            project_id=project.id,
        )
        self._db.flush()
        return plan

    def list_plans(self, project_id: UUID) -> list[MigrationWavePlan]:
        stmt = (
            select(MigrationWavePlan)
            .where(MigrationWavePlan.project_id == project_id)
            .order_by(MigrationWavePlan.created_at.desc())
        )
        return list(self._db.scalars(stmt))

    def get_plan(self, project_id: UUID, plan_id: UUID) -> MigrationWavePlan | None:
        plan = self._db.get(MigrationWavePlan, plan_id)
        if not plan or plan.project_id != project_id:
            return None
        return plan

    def pause_plan(self, plan: MigrationWavePlan, *, reason: str) -> MigrationWavePlan:
        plan.status = "paused"
        plan.pause_reason = reason
        self._cancel_queued_runs(plan)
        write_audit(
            self._db,
            entity_type="migration_wave_plan",
            entity_id=str(plan.id),
            action=AuditAction.STATUS_CHANGED,
            message="Wave plan paused",
            details={"reason": reason},
            project_id=plan.project_id,
        )
        self._db.flush()
        return plan

    def resume_plan(self, plan: MigrationWavePlan) -> MigrationWavePlan:
        if plan.status != "paused":
            raise ValueError(f"Cannot resume plan in status {plan.status!r}")

        project = self._db.get(Project, plan.project_id)
        if not project:
            raise ValueError("Project not found")

        plan.status = "active"
        plan.pause_reason = None

        runs_by_wave: dict[int, list[MigrationRun]] = {}
        for run in self._runs_for_plan(plan):
            wave_number = int((run.run_config or {}).get("wave_number") or 0)
            runs_by_wave.setdefault(wave_number, []).append(run)

        entity = plan.plan_config.get("entity", "account")
        accounts_per_wave = int(plan.plan_config.get("accounts_per_wave", 1000))
        base = {
            **plan.plan_config.get("run_config", {}),
            "entity": entity,
            "async": True,
            "use_selection": plan.plan_config.get("run_config", {}).get("use_selection", True),
            "candidate_limit": accounts_per_wave,
            "wave_plan_id": str(plan.id),
        }

        for wave_number in range(1, plan.total_waves + 1):
            if wave_number <= plan.waves_completed:
                continue
            wave_runs = runs_by_wave.get(wave_number, [])
            if any(
                r.status in (RunStatus.QUEUED.value, RunStatus.RUNNING.value, RunStatus.COMPLETED.value)
                for r in wave_runs
            ):
                continue
            self._queue_wave_run(
                project,
                plan,
                wave_number=wave_number,
                run_config={**base, "wave_number": wave_number},
            )
            plan.waves_queued += 1

        write_audit(
            self._db,
            entity_type="migration_wave_plan",
            entity_id=str(plan.id),
            action=AuditAction.STATUS_CHANGED,
            message="Wave plan resumed",
            project_id=plan.project_id,
        )
        self._db.flush()
        return plan

    def on_run_finished(self, run: MigrationRun) -> None:
        plan_id_raw = (run.run_config or {}).get("wave_plan_id")
        if not plan_id_raw:
            return

        plan = self._db.get(MigrationWavePlan, UUID(str(plan_id_raw)))
        if not plan or plan.status in ("completed", "cancelled"):
            return

        plan.last_run_id = run.id
        max_failure_pct = float(plan.plan_config.get("max_failure_pct", get_settings().wave_default_max_failure_pct))
        failure_pct = run_failure_pct(run)
        run_failed = run.status in (RunStatus.FAILED.value, RunStatus.CANCELLED.value)

        if run_failed:
            plan.waves_failed += 1
            self.pause_plan(
                plan,
                reason=run.error_message or f"Wave run {run.run_config.get('wave_number')} failed",
            )
            return

        if failure_pct > max_failure_pct:
            plan.waves_failed += 1
            self.pause_plan(
                plan,
                reason=(
                    f"Failure rate {failure_pct:.1f}% exceeded threshold {max_failure_pct}% "
                    f"(wave {run.run_config.get('wave_number')})"
                ),
            )
            return

        plan.waves_completed += 1
        if plan.waves_completed >= plan.total_waves:
            plan.status = "completed"
            plan.completed_at = _utcnow()
            write_audit(
                self._db,
                entity_type="migration_wave_plan",
                entity_id=str(plan.id),
                action=AuditAction.STATUS_CHANGED,
                message="Wave plan completed",
                details={
                    "waves_completed": plan.waves_completed,
                    "waves_failed": plan.waves_failed,
                },
                project_id=plan.project_id,
            )
        self._db.flush()

    def plan_status(self, plan: MigrationWavePlan) -> dict[str, Any]:
        runs = self._runs_for_plan(plan)
        return {
            "id": str(plan.id),
            "name": plan.name,
            "status": plan.status,
            "total_waves": plan.total_waves,
            "waves_queued": plan.waves_queued,
            "waves_completed": plan.waves_completed,
            "waves_failed": plan.waves_failed,
            "pause_reason": plan.pause_reason,
            "daily_capacity": plan.total_waves * int(plan.plan_config.get("accounts_per_wave", 0)),
            "plan_config": plan.plan_config,
            "runs": [
                {
                    "run_id": str(r.id),
                    "wave_number": (r.run_config or {}).get("wave_number"),
                    "status": r.status,
                    "failure_pct": run_failure_pct(r) if r.status != RunStatus.QUEUED.value else None,
                }
                for r in runs
            ],
        }

    def _check_health_gate(
        self,
        project: Project,
        *,
        entity: str,
        min_cohort_score: float,
        max_blocked_pct: float,
    ) -> None:
        assessment = AccountHealthService(self._db).latest_assessment(project.id, entity=entity)
        if not assessment or assessment.row_count == 0:
            raise WaveGateError(
                "Cohort readiness gate: run POST /account-health/assess before scheduling waves"
            )

        blocked = int((assessment.summary or {}).get("counts", {}).get("blocked", 0))
        blocked_pct = (100.0 * blocked / assessment.row_count) if assessment.row_count else 0.0
        if assessment.cohort_readiness_score < min_cohort_score:
            raise WaveGateError(
                f"Cohort readiness score {assessment.cohort_readiness_score} "
                f"below minimum {min_cohort_score}"
            )
        if blocked_pct > max_blocked_pct:
            raise WaveGateError(
                f"Blocked accounts {blocked_pct:.1f}% exceed maximum {max_blocked_pct}%"
            )

    def _queue_wave_run(
        self,
        project: Project,
        plan: MigrationWavePlan,
        *,
        wave_number: int,
        run_config: dict[str, Any],
    ) -> MigrationRun:
        run = MigrationRun(
            project_id=project.id,
            name=f"{plan.name} — wave {wave_number}/{plan.total_waves}",
            run_config=run_config,
            status=RunStatus.QUEUED.value,
            execution_mode="async",
            progress_message="Queued for wave worker",
        )
        run.batches.append(Batch(batch_number=1, batch_config={}))
        self._db.add(run)
        self._db.flush()
        write_audit(
            self._db,
            entity_type="migration_run",
            entity_id=str(run.id),
            action=AuditAction.CREATED,
            message=f"Wave {wave_number} queued",
            details={"wave_plan_id": str(plan.id), "wave_number": wave_number},
            project_id=project.id,
            run_id=run.id,
        )
        return run

    def _cancel_queued_runs(self, plan: MigrationWavePlan) -> int:
        cancelled = 0
        for run in self._runs_for_plan(plan):
            if run.status != RunStatus.QUEUED.value:
                continue
            run.status = RunStatus.CANCELLED.value
            run.progress_message = "Cancelled — wave plan paused"
            cancelled += 1
        return cancelled

    def _runs_for_plan(self, plan: MigrationWavePlan) -> list[MigrationRun]:
        plan_id = str(plan.id)
        stmt = select(MigrationRun).where(MigrationRun.project_id == plan.project_id)
        return [r for r in self._db.scalars(stmt) if (r.run_config or {}).get("wave_plan_id") == plan_id]
