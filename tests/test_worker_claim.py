"""Tests for parallel worker run claiming."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from migration_utility.core.enums import RunStatus
from migration_utility.datastore.base import Base
import migration_utility.datastore.models  # noqa: F401
from migration_utility.datastore.models import MigrationRun, Project
from migration_utility.worker.claim import claim_next_queued_run


@pytest.fixture()
def claim_env():
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

    project = Project(
        name="Worker Co",
        slug="worker-co",
        source_connector_key="mock",
        target_adapter_key="mock",
    )
    session = Session()
    session.add(project)
    session.commit()

    runs = []
    for idx in range(3):
        run = MigrationRun(
            project_id=project.id,
            name=f"Queued {idx}",
            status=RunStatus.QUEUED.value,
            run_config={"entity": "account"},
        )
        session.add(run)
        runs.append(run)
    session.commit()
    for run in runs:
        session.refresh(run)

    yield Session, project, [r.id for r in runs]
    session.close()


def test_claim_next_queued_run_marks_running(claim_env):
    Session, _project, run_ids = claim_env
    db = Session()
    claimed = claim_next_queued_run(db, worker_id="worker-a")
    assert claimed is not None
    assert claimed.id in run_ids
    assert claimed.status == RunStatus.RUNNING.value
    assert claimed.claimed_by == "worker-a"
    assert claimed.claimed_at is not None
    db.close()


def test_claim_returns_none_when_queue_empty(claim_env):
    Session, _project, _run_ids = claim_env
    db = Session()
    for _ in range(3):
        claim_next_queued_run(db, worker_id="worker-a")
    assert claim_next_queued_run(db, worker_id="worker-b") is None
    db.close()


def test_sequential_workers_claim_distinct_runs(claim_env):
    Session, _project, run_ids = claim_env
    claimed_ids: list = []
    for worker_id in ("w-0", "w-1", "w-2"):
        db = Session()
        run = claim_next_queued_run(db, worker_id=worker_id)
        db.close()
        if run:
            claimed_ids.append(run.id)

    assert len(claimed_ids) == 3
    assert set(claimed_ids) == set(run_ids)

    db = Session()
    remaining = db.scalars(
        select(MigrationRun).where(MigrationRun.status == RunStatus.QUEUED.value)
    ).all()
    assert remaining == []
    db.close()
