from __future__ import annotations

import logging
from typing import Callable
from uuid import UUID

from migration_utility.connectors.base import SourceConnector, TargetAdapter
from migration_utility.connectors.registry import ConnectorRegistry
from migration_utility.core.context import PipelineResult, StageResult
from migration_utility.core.enums import PipelineStage
from migration_utility.core.events import EventBus, PipelineEvent, RunContext
from migration_utility.rules.pipeline_hooks import run_ingest, run_load, run_transform, run_validate

logger = logging.getLogger(__name__)

StageHandler = Callable[[RunContext, SourceConnector, TargetAdapter], StageResult]


class MigrationPipeline:
    """
    Orchestrates ingest → validate → transform → load.

    Each stage resolves connectors from the registry and delegates to
    registered stage handlers (defaults provided; override per project).
    """

    def __init__(
        self,
        registry: ConnectorRegistry,
        event_bus: EventBus | None = None,
    ) -> None:
        self._registry = registry
        self._event_bus = event_bus or EventBus()
        self._handlers: dict[PipelineStage, StageHandler] = {
            PipelineStage.INGEST: run_ingest,
            PipelineStage.VALIDATE: run_validate,
            PipelineStage.TRANSFORM: run_transform,
            PipelineStage.LOAD: run_load,
        }

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    def set_stage_handler(self, stage: PipelineStage, handler: StageHandler) -> None:
        self._handlers[stage] = handler

    def run(self, ctx: RunContext) -> PipelineResult:
        run_id = str(ctx.run_id)
        stages: list[StageResult] = []

        try:
            source = self._registry.get_source(ctx.source_connector_key)
            target = self._registry.get_target(ctx.target_adapter_key)
        except KeyError as exc:
            return PipelineResult(run_id=run_id, success=False, error=str(exc))

        for stage in PipelineStage:
            self._emit(stage.value, ctx, "started")
            try:
                result = self._handlers[stage](ctx, source, target)
                stages.append(result)
                if result.success:
                    self._emit(stage.value, ctx, "completed", result.message)
                else:
                    self._emit(stage.value, ctx, "failed", result.message)
                    return PipelineResult(
                        run_id=run_id,
                        success=False,
                        stages=stages,
                        error=result.message,
                    )
            except Exception as exc:
                logger.exception("Pipeline stage %s failed", stage.value)
                failed = StageResult(
                    stage=stage.value,
                    success=False,
                    message=str(exc),
                )
                stages.append(failed)
                self._emit(stage.value, ctx, "failed", str(exc))
                return PipelineResult(
                    run_id=run_id,
                    success=False,
                    stages=stages,
                    error=str(exc),
                )

        return PipelineResult(run_id=run_id, success=True, stages=stages)

    def _emit(
        self,
        stage: str,
        ctx: RunContext,
        status: str,
        message: str = "",
    ) -> None:
        self._event_bus.publish(
            PipelineEvent(
                stage=stage,
                run_id=ctx.run_id,
                batch_id=ctx.batch_id,
                status=status,
                message=message,
            )
        )
