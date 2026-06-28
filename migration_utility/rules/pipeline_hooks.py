from __future__ import annotations

from typing import Any

from migration_utility.connectors.base import SourceConnector, TargetAdapter
from migration_utility.core.context import StageResult
from migration_utility.core.enums import PipelineStage
from migration_utility.core.events import RunContext
from migration_utility.rules.engine import TransformEngine, ValidationEngine
from migration_utility.rules.types import LoadedRuleSet
from migration_utility.transforms.stw import get_stw_rules


def _transform_context(ctx: RunContext) -> dict[str, Any]:
    stw = get_stw_rules(ctx.config)
    tariff_table = ctx.config.get("stw_tariff_table") or ctx.metadata.get("tariff_table") or []
    if tariff_table:
        stw = dict(stw)
        stw["rateband"] = {**stw["rateband"], "tariff_table": tariff_table}
    return {
        "stw_transform_rules": stw,
        "tariff_table": tariff_table,
        "tariff_mappings": ctx.config.get("tariff_mappings") or ctx.metadata.get("tariff_mappings") or {},
    }


def _get_records(ctx: RunContext, source: SourceConnector) -> list[dict[str, Any]]:
    cached = ctx.metadata.get("pipeline_records")
    if cached is not None:
        return cached
    records = source.extract(ctx)
    ctx.metadata["pipeline_records"] = records
    return records


def run_validate(
    ctx: RunContext,
    source: SourceConnector,
    target: TargetAdapter,
) -> StageResult:
    records = _get_records(ctx, source)
    rule_set: LoadedRuleSet | None = ctx.metadata.get("rule_set")

    if rule_set and rule_set.validation_rules:
        engine = ValidationEngine()
        valid, invalid, reasons = engine.apply(records, rule_set.validation_rules)
        ctx.metadata["validated_records"] = valid
        ctx.metadata["validation_failures"] = list(zip(invalid, reasons))
        allow_errors = ctx.config.get("allow_validation_errors", False)
        return StageResult(
            stage=PipelineStage.VALIDATE.value,
            success=len(invalid) == 0 or allow_errors,
            records_processed=len(valid),
            records_failed=len(invalid),
            message=f"Rules validated {len(valid)} ok, {len(invalid)} failed",
            details={"rule_set": rule_set.name, "failures": reasons[:5]},
        )

    valid, invalid = source.validate(records, ctx)
    ctx.metadata["validated_records"] = valid
    allow_errors = ctx.config.get("allow_validation_errors", False)
    return StageResult(
        stage=PipelineStage.VALIDATE.value,
        success=len(invalid) == 0 or allow_errors,
        records_processed=len(valid),
        records_failed=len(invalid),
        message=f"Validated {len(valid)} ok, {len(invalid)} failed",
    )


def run_transform(
    ctx: RunContext,
    source: SourceConnector,
    target: TargetAdapter,
) -> StageResult:
    valid = ctx.metadata.get("validated_records")
    if valid is None:
        records = _get_records(ctx, source)
        valid, _ = source.validate(records, ctx)

    rule_set: LoadedRuleSet | None = ctx.metadata.get("rule_set")

    if rule_set and rule_set.field_mappings:
        engine = TransformEngine()
        transformed = engine.apply(valid, rule_set.field_mappings, context=_transform_context(ctx))
    else:
        transformed = source.transform(valid, ctx)

    ctx.metadata["transformed_records"] = transformed
    return StageResult(
        stage=PipelineStage.TRANSFORM.value,
        success=True,
        records_processed=len(transformed),
        message=f"Transformed {len(transformed)} record(s)",
        details={"rule_set": rule_set.name if rule_set else None},
    )


def run_ingest(
    ctx: RunContext,
    source: SourceConnector,
    target: TargetAdapter,
) -> StageResult:
    records = _get_records(ctx, source)
    return StageResult(
        stage=PipelineStage.INGEST.value,
        success=True,
        records_processed=len(records),
        message=f"Ingested {len(records)} record(s)",
        details={"sample_keys": list(records[0].keys()) if records else []},
    )


def run_load(
    ctx: RunContext,
    source: SourceConnector,
    target: TargetAdapter,
) -> StageResult:
    transformed = ctx.metadata.get("transformed_records", [])
    if not transformed:
        records = _get_records(ctx, source)
        valid, _ = source.validate(records, ctx)
        rule_set: LoadedRuleSet | None = ctx.metadata.get("rule_set")
        if rule_set and rule_set.field_mappings:
            transformed = TransformEngine().apply(
                valid, rule_set.field_mappings, context=_transform_context(ctx)
            )
        else:
            transformed = source.transform(valid, ctx)

    loaded, failed = target.load(transformed, ctx)
    ctx.metadata["load_results"] = {"loaded": loaded, "failed": failed}
    return StageResult(
        stage=PipelineStage.LOAD.value,
        success=len(failed) == 0,
        records_processed=len(loaded),
        records_failed=len(failed),
        message=f"Loaded {len(loaded)} ok, {len(failed)} failed",
    )
