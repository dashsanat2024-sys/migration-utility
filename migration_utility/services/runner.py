from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from migration_utility.config import get_settings
from migration_utility.connectors.registry import ConnectorRegistry
from migration_utility.core.enums import AuditAction, BatchStatus, CandidateStatus, RunStatus
from migration_utility.core.events import EventBus, RunContext
from migration_utility.core.pipeline import MigrationPipeline
from migration_utility.datastore.models import Batch, MigrationRun, Project
from migration_utility.datastore.session import get_engine
from migration_utility.exceptions.service import ExceptionQueueService
from migration_utility.ingest.staging import count_staged_rows_for_batch, staging_table_name
from migration_utility.rules.loader import RuleLoader
from migration_utility.selection.service import CandidateService
from migration_utility.services.load_records import LoadRecordService
from migration_utility.waves.service import WaveOrchestratorService, run_failure_pct

logger = logging.getLogger(__name__)

_STAGE_PROGRESS = {
    "ingest": (10, "Ingesting staged records"),
    "validate": (40, "Validating records"),
    "transform": (70, "Transforming records"),
    "load": (95, "Loading to destination"),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


from migration_utility.services.audit import write_audit


class RunService:
    """Executes migration runs and persists status + audit trail."""

    def __init__(self, db: Session, registry: ConnectorRegistry) -> None:
        self._db = db
        self._registry = registry

    def execute_run(self, run: MigrationRun, project: Project) -> MigrationRun:
        run.status = RunStatus.RUNNING.value
        run.started_at = _utcnow()
        run.progress_pct = 0
        run.progress_message = "Run started"
        run.error_message = None
        write_audit(
            self._db,
            entity_type="migration_run",
            entity_id=str(run.id),
            action=AuditAction.STATUS_CHANGED,
            message="Run started",
            project_id=project.id,
            run_id=run.id,
        )
        self._db.flush()

        event_bus = EventBus()
        event_bus.subscribe(lambda e: self._on_pipeline_event(run, project, e))

        pipeline = MigrationPipeline(self._registry, event_bus)
        merged_config = {**project.config, **run.run_config}
        entity = merged_config.get("entity", "account")
        rule_loader = RuleLoader(self._db)

        loaded_rule_set = None
        if merged_config.get("use_rules", True):
            try:
                rule_set_id = merged_config.get("rule_set_id")
                rs_uuid = UUID(str(rule_set_id)) if rule_set_id else None
                loaded_rule_set = rule_loader.load_for_run(
                    project.id,
                    entity,
                    rule_set_id=rs_uuid,
                    require_approved=merged_config.get("require_approved_rules", True),
                )
            except ValueError as exc:
                if merged_config.get("block_unapproved_rules", False):
                    run.status = RunStatus.FAILED.value
                    run.error_message = str(exc)
                    run.completed_at = _utcnow()
                    self._db.commit()
                    self._finalize_run(run, project)
                    return run

        candidate_service = CandidateService(self._db)
        use_selection = merged_config.get("use_selection", False)
        resume_checkpoint = merged_config.pop("resume_from_checkpoint", None) or {}

        for batch in sorted(run.batches, key=lambda b: b.batch_number):
            batch.status = BatchStatus.RUNNING.value
            self._db.flush()

            batch_config = {**merged_config, "filter_batch_id": str(batch.id), "chunk_size": get_settings().run_chunk_size}

            if use_selection:
                try:
                    profile_id = merged_config.get("selection_profile_id")
                    rs_uuid = UUID(str(profile_id)) if profile_id else None
                    count = candidate_service.populate_batch(
                        project,
                        batch,
                        entity,
                        profile_id=rs_uuid,
                        limit=merged_config.get("candidate_limit"),
                    )
                    self._db.commit()
                    self._db.expire(batch)
                    if count == 0 and merged_config.get("require_candidates", False):
                        batch.status = BatchStatus.FAILED.value
                        batch.stats = {"success": False, "message": "No candidates matched selection"}
                        run.status = RunStatus.FAILED.value
                        run.error_message = "No candidates matched selection criteria"
                        run.completed_at = _utcnow()
                        self._db.commit()
                        self._finalize_run(run, project)
                        return run
                except ValueError as exc:
                    run.status = RunStatus.FAILED.value
                    run.error_message = str(exc)
                    run.completed_at = _utcnow()
                    self._db.commit()
                    self._finalize_run(run, project)
                    return run

            ctx_metadata = {
                    "batch_number": batch.batch_number,
                    "project_slug": project.slug,
                    "rule_set": loaded_rule_set,
                    "target_system": project.target_system,
                    "environment": project.environment,
                }
            if merged_config.get("load_idempotent", get_settings().load_idempotent):
                ctx_metadata["loaded_external_ids"] = LoadRecordService(
                    self._db
                ).loaded_external_ids(project.id, entity=entity)

            ctx = RunContext(
                project_id=project.id,
                run_id=run.id,
                batch_id=batch.id,
                source_connector_key=project.source_connector_key,
                target_adapter_key=project.target_adapter_key,
                config=batch_config,
                metadata=ctx_metadata,
            )

            batch_outcome = self._execute_batch_pipeline(
                run=run,
                project=project,
                batch=batch,
                batch_config=batch_config,
                ctx=ctx,
                pipeline=pipeline,
                entity=entity,
                resume_checkpoint=resume_checkpoint,
            )

            failures = batch_outcome["validation_failures"]
            if failures:
                exc_svc = ExceptionQueueService(self._db)
                for idx, item in enumerate(failures[:200]):
                    if isinstance(item, tuple) and len(item) == 2:
                        invalid, reason = item
                    else:
                        continue
                    exc_svc.create_validation_exception(
                        project_id=project.id,
                        run_id=run.id,
                        entity=entity,
                        row_number=idx + 1,
                        payload=invalid if isinstance(invalid, dict) else {"value": invalid},
                        error_reason=str(reason),
                    )

            load_results = batch_outcome["load_results"]
            load_summary = None
            if load_results:
                loaded_count = len(load_results.get("loaded", []))
                failed_count = len(load_results.get("failed", []))
                if load_results.get("failed"):
                    from migration_utility.fallout.service import FalloutService

                    fallout_svc = FalloutService(self._db)
                    for failed_rec in load_results.get("failed", [])[:200]:
                        if isinstance(failed_rec, dict):
                            fallout_svc.classify_load_failure(
                                failed_rec,
                                entity=entity,
                                project_id=project.id,
                                run_id=run.id,
                            )
                try:
                    with self._db.begin_nested():
                        LoadRecordService(self._db).persist_results(
                            project,
                            run_id=run.id,
                            batch_id=batch.id,
                            target_adapter_key=project.target_adapter_key,
                            entity=entity,
                            loaded=load_results.get("loaded", []),
                            failed=load_results.get("failed", []),
                            audit_mode=merged_config.get(
                                "load_audit_mode", get_settings().load_audit_mode
                            ),
                            sample_size=merged_config.get(
                                "load_audit_sample_size", get_settings().load_audit_sample_size
                            ),
                        )
                    load_summary = {
                        "loaded": loaded_count,
                        "failed": failed_count,
                        "persisted": True,
                        "audit_mode": merged_config.get(
                            "load_audit_mode", get_settings().load_audit_mode
                        ),
                    }
                except Exception as exc:
                    logger.warning("Load record persistence skipped: %s", exc)
                    load_summary = {
                        "loaded": loaded_count,
                        "failed": failed_count,
                        "persisted": False,
                        "persist_error": str(exc)[:200],
                    }

            batch.stats = {
                "success": batch_outcome["success"],
                "candidate_count": batch.batch_config.get("candidate_count"),
                "chunks_processed": batch_outcome.get("chunks_processed", 1),
                "records_processed": batch_outcome.get("records_processed", 0),
                "load_summary": load_summary,
                "stages": batch_outcome["stages"],
            }
            batch.status = (
                BatchStatus.COMPLETED.value if batch_outcome["success"] else BatchStatus.FAILED.value
            )
            self._update_candidate_statuses(
                candidate_service, batch.id, batch_outcome["success"]
            )
            self._db.flush()

            if not batch_outcome["success"]:
                run.status = RunStatus.FAILED.value
                run.error_message = batch_outcome.get("error")
                run.completed_at = _utcnow()
                run.progress_message = "Run failed"
                run.result_summary = {"batches_completed": batch.batch_number, "failed": True}
                run.checkpoint = {
                    **(run.checkpoint or {}),
                    "last_batch": batch.batch_number,
                    "resume_allowed": True,
                }
                self._db.commit()
                self._finalize_run(run, project)
                return run

            resume_checkpoint = {}
            run.checkpoint = {
                **(run.checkpoint or {}),
                "batch_id": str(batch.id),
                "last_row_number": batch_outcome.get("last_row_number", 0),
                "resume_allowed": True,
            }

        run.checkpoint = {k: v for k, v in (run.checkpoint or {}).items() if k != "resume_from_checkpoint"}
        loaded_total, failed_total = self._aggregate_load_counts(run)
        run.status = RunStatus.COMPLETED.value
        run.completed_at = _utcnow()
        run.progress_pct = 100
        run.progress_message = "Run completed"
        run.result_summary = {
            "batches_completed": len(run.batches),
            "total_processed": sum(
                (b.stats or {}).get("records_processed", 0) for b in run.batches if b.stats
            ),
            "loaded": loaded_total,
            "failed": failed_total,
            "failure_pct": round(run_failure_pct(run), 2),
        }
        write_audit(
            self._db,
            entity_type="migration_run",
            entity_id=str(run.id),
            action=AuditAction.STATUS_CHANGED,
            message="Run completed",
            details=run.result_summary,
            project_id=project.id,
            run_id=run.id,
        )
        self._db.commit()
        self._db.refresh(run)
        self._finalize_run(run, project)
        return run

    def _aggregate_load_counts(self, run: MigrationRun) -> tuple[int, int]:
        loaded = failed = 0
        for batch in run.batches:
            load_summary = (batch.stats or {}).get("load_summary") or {}
            loaded += int(load_summary.get("loaded", 0))
            failed += int(load_summary.get("failed", 0))
        return loaded, failed

    def _finalize_run(self, run: MigrationRun, project: Project) -> None:
        if run.status in (RunStatus.FAILED.value,) and run.result_summary is None:
            loaded, failed = self._aggregate_load_counts(run)
            run.result_summary = {
                "failed": True,
                "loaded": loaded,
                "failed_count": failed,
                "failure_pct": round(run_failure_pct(run), 2),
            }
        try:
            WaveOrchestratorService(self._db).on_run_finished(run)
            self._db.commit()
        except Exception:
            logger.exception("Wave plan update failed for run %s", run.id)

    def _execute_batch_pipeline(
        self,
        *,
        run: MigrationRun,
        project: Project,
        batch: Batch,
        batch_config: dict[str, Any],
        ctx: RunContext,
        pipeline: MigrationPipeline,
        entity: str,
        resume_checkpoint: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Run ingest→validate→transform→load, chunking when reading from staging."""
        use_chunks = project.source_connector_key == "staging"
        chunk_size = int(batch_config.get("chunk_size") or get_settings().run_chunk_size)

        after_row_number = 0
        if resume_checkpoint.get("batch_id") == str(batch.id):
            after_row_number = int(resume_checkpoint.get("last_row_number") or 0)

        batch_total = 0
        if use_chunks:
            batch_total = count_staged_rows_for_batch(
                get_engine(),
                staging_table_name(project.slug, entity),
                project_id=project.id,
                batch_id=batch.id,
            )

        all_validation_failures: list[Any] = []
        all_loaded: list[dict[str, Any]] = []
        all_failed: list[dict[str, Any]] = []
        stage_summaries: list[dict[str, Any]] = []
        chunks_processed = 0
        records_processed = 0
        last_row_number = after_row_number

        while True:
            chunk_config = {
                **batch_config,
                "after_row_number": after_row_number,
                "chunk_index": chunks_processed if use_chunks else None,
            }
            chunk_ctx = RunContext(
                project_id=ctx.project_id,
                run_id=ctx.run_id,
                batch_id=ctx.batch_id,
                source_connector_key=ctx.source_connector_key,
                target_adapter_key=ctx.target_adapter_key,
                config=chunk_config,
                metadata=dict(ctx.metadata),
            )
            result = pipeline.run(chunk_ctx)
            chunks_processed += 1

            failures = chunk_ctx.metadata.get("validation_failures") or []
            all_validation_failures.extend(failures)

            load_results = chunk_ctx.metadata.get("load_results") or {}
            all_loaded.extend(load_results.get("loaded", []))
            all_failed.extend(load_results.get("failed", []))
            records_processed += result.total_processed

            for stage in result.stages:
                stage_summaries.append(
                    {
                        "stage": stage.stage,
                        "success": stage.success,
                        "records_processed": stage.records_processed,
                        "records_failed": stage.records_failed,
                        "message": stage.message,
                        "chunk": chunks_processed,
                    }
                )

            if not result.success:
                run.checkpoint = {
                    **(run.checkpoint or {}),
                    "batch_id": str(batch.id),
                    "last_batch": batch.batch_number,
                    "last_row_number": after_row_number,
                    "resume_allowed": True,
                }
                return {
                    "success": False,
                    "error": result.error,
                    "validation_failures": all_validation_failures,
                    "load_results": {"loaded": all_loaded, "failed": all_failed},
                    "stages": stage_summaries,
                    "chunks_processed": chunks_processed,
                    "records_processed": records_processed,
                    "last_row_number": after_row_number,
                }

            if not use_chunks:
                last_row_number = int(chunk_ctx.metadata.get("last_row_number") or 0)
                break

            chunk_count = int(chunk_ctx.metadata.get("chunk_row_count") or 0)
            if chunk_count == 0:
                break

            new_last = int(chunk_ctx.metadata.get("last_row_number") or after_row_number)
            if new_last <= after_row_number:
                break

            after_row_number = new_last
            last_row_number = after_row_number
            run.checkpoint = {
                **(run.checkpoint or {}),
                "batch_id": str(batch.id),
                "last_batch": batch.batch_number,
                "last_row_number": after_row_number,
                "resume_allowed": True,
            }
            if batch_total > 0:
                done = min(after_row_number, batch_total)
                run.progress_pct = min(95, 10 + int(85 * done / batch_total))
                run.progress_message = f"Processed {done}/{batch_total} staged row(s)"
            else:
                run.progress_message = f"Processed chunk {chunks_processed}"
            self._db.flush()

        return {
            "success": True,
            "error": None,
            "validation_failures": all_validation_failures,
            "load_results": {"loaded": all_loaded, "failed": all_failed},
            "stages": stage_summaries,
            "chunks_processed": chunks_processed,
            "records_processed": records_processed,
            "last_row_number": last_row_number,
        }

    def _update_candidate_statuses(
        self,
        candidate_service: CandidateService,
        batch_id: UUID,
        success: bool,
    ) -> None:
        new_status = (
            CandidateStatus.LOADED.value if success else CandidateStatus.FAILED.value
        )
        for candidate in candidate_service.list_for_batch(batch_id):
            candidate.status = new_status
            candidate.status_history = [
                *(candidate.status_history or []),
                {"status": new_status, "message": "Batch pipeline finished"},
            ]

    def _on_pipeline_event(self, run: MigrationRun, project: Project, event) -> None:
        pct, msg = _STAGE_PROGRESS.get(event.stage, (run.progress_pct, event.stage))
        if event.status == "completed":
            run.progress_pct = pct
            run.progress_message = msg
        elif event.status == "started" and event.stage in _STAGE_PROGRESS:
            run.progress_message = f"Starting {event.stage}"
        write_audit(
            self._db,
            entity_type="pipeline",
            entity_id=str(run.id),
            action=AuditAction.PIPELINE_STAGE,
            message=f"{event.stage}: {event.status}",
            details={
                "stage": event.stage,
                "status": event.status,
                "batch_id": str(event.batch_id) if event.batch_id else None,
            },
            project_id=project.id,
            run_id=run.id,
        )
        self._db.flush()
