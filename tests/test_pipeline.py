from uuid import uuid4

import pytest

from migration_utility.connectors.registry import build_default_registry
from migration_utility.core.events import RunContext
from migration_utility.core.pipeline import MigrationPipeline


def test_pipeline_runs_all_stages():
    registry = build_default_registry()
    pipeline = MigrationPipeline(registry)
    ctx = RunContext(
        project_id=uuid4(),
        run_id=uuid4(),
        batch_id=uuid4(),
        source_connector_key="mock",
        target_adapter_key="mock",
        config={"mock_record_count": 2},
    )
    result = pipeline.run(ctx)
    assert result.success is True
    assert len(result.stages) == 4
    assert result.total_processed > 0


def test_pipeline_fails_on_unknown_connector():
    registry = build_default_registry()
    pipeline = MigrationPipeline(registry)
    ctx = RunContext(
        project_id=uuid4(),
        run_id=uuid4(),
        batch_id=None,
        source_connector_key="nonexistent",
        target_adapter_key="mock",
    )
    result = pipeline.run(ctx)
    assert result.success is False
    assert "Unknown source connector" in (result.error or "")
