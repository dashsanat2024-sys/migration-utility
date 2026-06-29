"""Tests for bulk load audit persistence and summary mode."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from migration_utility.datastore.base import Base
import migration_utility.datastore.models  # noqa: F401
from migration_utility.datastore.models import LoadRecord, Project
from migration_utility.services.load_records import LoadRecordService


@pytest.fixture()
def audit_env(monkeypatch):
    monkeypatch.setenv("LOAD_AUDIT_MODE", "full")
    from migration_utility.config import get_settings

    get_settings.cache_clear()

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
        name="Audit Co",
        slug="audit-co",
        source_connector_key="mock",
        target_adapter_key="kraken",
    )
    session.add(project)
    session.commit()
    yield session, project
    session.close()
    get_settings.cache_clear()


def _records(n: int, prefix: str = "ACC") -> list[dict]:
    return [
        {"accountId": f"{prefix}-{i:03d}", "accountName": f"Co {i}", "importStatus": "accepted"}
        for i in range(1, n + 1)
    ]


def test_persist_results_bulk_inserts_all_rows(audit_env):
    session, project = audit_env
    run_id = uuid4()
    batch_id = uuid4()
    svc = LoadRecordService(session)
    count = svc.persist_results(
        project,
        run_id=run_id,
        batch_id=batch_id,
        target_adapter_key="kraken",
        entity="account",
        loaded=_records(25),
        failed=_records(3, prefix="FAIL"),
        audit_mode="full",
    )
    assert count == 28
    db_count = session.scalar(
        select(func.count()).select_from(LoadRecord).where(LoadRecord.run_id == run_id)
    )
    assert db_count == 28


def test_summary_mode_persists_samples_and_summary_row(audit_env):
    session, project = audit_env
    run_id = uuid4()
    batch_id = uuid4()
    svc = LoadRecordService(session)
    count = svc.persist_results(
        project,
        run_id=run_id,
        batch_id=batch_id,
        target_adapter_key="kraken",
        entity="account",
        loaded=_records(50),
        failed=_records(5, prefix="FAIL"),
        audit_mode="summary",
        sample_size=10,
    )
    # 10 loaded samples + 5 failed samples + 1 summary row
    assert count == 16

    summary = svc.summary_for_run(run_id)
    assert summary["audit_mode"] == "summary"
    assert summary["loaded"] == 50
    assert summary["failed"] == 5
    assert summary["total"] == 55

    listed = svc.list_for_run(run_id)
    assert len(listed) == 15
    assert all(r.status in ("loaded", "failed") for r in listed)
