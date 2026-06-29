"""Tests for load idempotency / URN dedup."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from migration_utility.connectors.idempotency import (
    build_record_idempotency_key,
    partition_idempotent,
)
from migration_utility.connectors.kraken import KrakenTargetAdapter, KrakenClient
from migration_utility.core.events import RunContext
from migration_utility.datastore.base import Base
import migration_utility.datastore.models  # noqa: F401
from migration_utility.datastore.models import LoadRecord, Project
from migration_utility.services.load_records import LoadRecordService


@pytest.fixture()
def idempotency_env():
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
    Session = sessionmaker(bind=engine)
    session = Session()
    project = Project(
        name="Idem Co",
        slug="idem-co",
        source_connector_key="staging",
        target_adapter_key="kraken",
        target_system="kraken",
    )
    session.add(project)
    session.commit()
    yield session, project
    session.close()


def test_build_record_idempotency_key_stable():
    pid = uuid4()
    record = {"accountId": "ACC-001", "accountName": "Test", "accountStatus": "ACTIVE"}
    key = build_record_idempotency_key(pid, "account", record)
    assert key == f"{pid}:account:ACC-001"


def test_partition_idempotent_skips_known_urns():
    pid = uuid4()
    records = [
        {"accountId": "ACC-001", "accountName": "A", "accountStatus": "ACTIVE"},
        {"accountId": "ACC-002", "accountName": "B", "accountStatus": "ACTIVE"},
    ]
    to_load, skipped = partition_idempotent(records, {"ACC-001"}, entity="account", project_id=pid)
    assert len(to_load) == 1
    assert to_load[0]["accountId"] == "ACC-002"
    assert len(skipped) == 1
    assert skipped[0]["importStatus"] == "already_loaded"


def test_kraken_adapter_skips_already_loaded(idempotency_env):
    session, project = idempotency_env
    session.add(
        LoadRecord(
            project_id=project.id,
            target_adapter_key="kraken",
            entity="account",
            external_id="ACC-100",
            status="loaded",
            idempotency_key=f"{project.id}:account:ACC-100",
        )
    )
    session.commit()

    adapter = KrakenTargetAdapter(client=KrakenClient(mock=True))
    ctx = RunContext(
        project_id=project.id,
        run_id=uuid4(),
        batch_id=uuid4(),
        source_connector_key="staging",
        target_adapter_key="kraken",
        config={"entity": "account", "load_idempotent": True},
        metadata={
            "target_system": "kraken",
            "environment": "dev",
            "loaded_external_ids": LoadRecordService(session).loaded_external_ids(
                project.id, entity="account"
            ),
        },
    )
    records = [
        {"accountId": "ACC-100", "accountName": "Existing", "accountStatus": "ACTIVE"},
        {"accountId": "ACC-101", "accountName": "New", "accountStatus": "ACTIVE"},
    ]
    loaded, failed = adapter.load(records, ctx)
    assert len(failed) == 0
    assert len(loaded) == 2
    statuses = {r["accountId"]: r.get("importStatus") for r in loaded}
    assert statuses["ACC-100"] == "already_loaded"
    assert statuses["ACC-101"] == "accepted"
    assert ctx.metadata["load_skipped_idempotent"] == 1
