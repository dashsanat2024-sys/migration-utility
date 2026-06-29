"""Tests for chunked staging reads and batch pipeline chunking."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from migration_utility.connectors.staging import StagingSourceConnector
from migration_utility.connectors.staging import StagingSourceConnector
from migration_utility.core.events import RunContext
from migration_utility.datastore.base import Base
import migration_utility.datastore.models  # noqa: F401
from migration_utility.ingest.staging import (
    count_staged_rows_for_batch,
    ensure_staging_table,
    fetch_staged_rows,
    insert_staged_rows,
    staging_table_name,
)
from migration_utility.schema.registry import build_default_schema_registry


@pytest.fixture()
def staging_env():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if column.type.__class__.__name__ == "JSONB":
                from sqlalchemy import JSON

                column.type = JSON()
    Base.metadata.create_all(bind=engine)
    registry = build_default_schema_registry()
    project_id = uuid4()
    project_slug = f"chunk-{uuid4().hex[:8]}"
    entity = registry.get("account")
    table_name = staging_table_name(project_slug, "account")
    table = ensure_staging_table(engine, table_name, entity)
    batch_id = uuid4()
    rows = [
        {"id": f"ACC-{i:03d}", "name": f"User {i}", "status": "active"}
        for i in range(1, 6)
    ]
    with engine.begin() as conn:
        insert_staged_rows(
            conn,
            table,
            project_id=project_id,
            source_file_id=uuid4(),
            rows=rows,
            row_numbers=list(range(1, 6)),
            batch_id=batch_id,
        )
    yield engine, project_id, project_slug, table_name, batch_id


def test_fetch_staged_rows_chunks(staging_env):
    engine, project_id, _project_slug, table_name, batch_id = staging_env

    first = fetch_staged_rows(
        engine,
        table_name,
        project_id=project_id,
        batch_id=batch_id,
        after_row_number=0,
        limit=2,
    )
    assert len(first) == 2
    assert first[0]["_row_number"] == 1
    assert first[1]["_row_number"] == 2

    second = fetch_staged_rows(
        engine,
        table_name,
        project_id=project_id,
        batch_id=batch_id,
        after_row_number=int(first[-1]["_row_number"]),
        limit=2,
    )
    assert len(second) == 2
    assert second[0]["_row_number"] == 3

    third = fetch_staged_rows(
        engine,
        table_name,
        project_id=project_id,
        batch_id=batch_id,
        after_row_number=int(second[-1]["_row_number"]),
        limit=2,
    )
    assert len(third) == 1
    assert third[0]["_row_number"] == 5


def test_count_staged_rows_for_batch(staging_env):
    engine, project_id, _project_slug, table_name, batch_id = staging_env
    assert (
        count_staged_rows_for_batch(
            engine, table_name, project_id=project_id, batch_id=batch_id
        )
        == 5
    )


def test_staging_connector_sets_chunk_metadata(staging_env, monkeypatch):
    engine, project_id, project_slug, _table_name, batch_id = staging_env
    monkeypatch.setattr("migration_utility.connectors.staging.get_engine", lambda: engine)

    registry = build_default_schema_registry()
    connector = StagingSourceConnector(registry)
    ctx = RunContext(
        project_id=project_id,
        run_id=uuid4(),
        batch_id=batch_id,
        source_connector_key="staging",
        target_adapter_key="mock",
        config={
            "entity": "account",
            "filter_batch_id": str(batch_id),
            "chunk_size": 2,
            "after_row_number": 0,
        },
        metadata={"project_slug": project_slug},
    )
    records = connector.extract(ctx)
    assert len(records) == 2
    assert ctx.metadata["chunk_row_count"] == 2
    assert ctx.metadata["last_row_number"] == 2
