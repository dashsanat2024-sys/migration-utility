"""Tests for staging table indexes."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool

from migration_utility.ingest.staging import (
    ensure_staging_indexes,
    ensure_staging_table,
    staging_table_name,
)
from migration_utility.schema.registry import build_default_schema_registry


@pytest.fixture()
def staging_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine


def test_ensure_staging_table_creates_indexes(staging_engine):
    registry = build_default_schema_registry()
    entity = registry.get("account")
    table_name = staging_table_name("index-co", "account")
    ensure_staging_table(staging_engine, table_name, entity)

    indexes = {idx["name"] for idx in inspect(staging_engine).get_indexes(table_name)}
    assert any("proj_status_batch" in name for name in indexes)
    assert any("proj_status_batch_row" in name for name in indexes)


def test_ensure_staging_indexes_idempotent(staging_engine):
    registry = build_default_schema_registry()
    entity = registry.get("account")
    table_name = staging_table_name("index-co-2", "account")
    ensure_staging_table(staging_engine, table_name, entity)
    ensure_staging_indexes(staging_engine, table_name)
    indexes_after = inspect(staging_engine).get_indexes(table_name)
    ensure_staging_indexes(staging_engine, table_name)
    assert len(inspect(staging_engine).get_indexes(table_name)) == len(indexes_after)
