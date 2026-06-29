"""Tests for wave orchestration (Phase 5)."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from migration_utility.core.enums import RunStatus
from migration_utility.datastore.base import Base
import migration_utility.datastore.models  # noqa: F401
from migration_utility.datastore.models import (
    AccountHealthAssessment,
    Batch,
    MigrationRun,
    MigrationWavePlan,
    Project,
)
from migration_utility.waves.service import WaveGateError, WaveOrchestratorService, run_failure_pct


@pytest.fixture()
def wave_env(monkeypatch):
    monkeypatch.setenv("WAVE_REQUIRE_HEALTH_GATE", "false")
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
        name="Wave Co",
        slug="wave-co",
        source_connector_key="mock",
        target_adapter_key="mock",
    )
    session.add(project)
    session.commit()
    yield session, project
    session.close()
    get_settings.cache_clear()


def test_create_wave_plan_queues_runs(wave_env):
    session, project = wave_env
    svc = WaveOrchestratorService(session)
    plan = svc.create_plan(
        project,
        name="Day 1",
        wave_count=3,
        accounts_per_wave=5000,
        run_config={"use_rules": False, "use_selection": False},
    )
    session.commit()

    assert plan.total_waves == 3
    assert plan.waves_queued == 3
    assert plan.status == "active"

    runs = session.query(MigrationRun).filter(MigrationRun.project_id == project.id).all()
    assert len(runs) == 3
    assert all(r.status == RunStatus.QUEUED.value for r in runs)
    assert all(r.run_config.get("wave_plan_id") == str(plan.id) for r in runs)


def test_health_gate_blocks_without_assessment(wave_env, monkeypatch):
    session, project = wave_env
    monkeypatch.setenv("WAVE_REQUIRE_HEALTH_GATE", "true")
    from migration_utility.config import get_settings

    get_settings.cache_clear()
    svc = WaveOrchestratorService(session)
    with pytest.raises(WaveGateError):
        svc.create_plan(
            project,
            name="Gated",
            wave_count=1,
            accounts_per_wave=100,
            require_health_gate=True,
        )


def test_health_gate_passes_with_assessment(wave_env, monkeypatch):
    session, project = wave_env
    monkeypatch.setenv("WAVE_REQUIRE_HEALTH_GATE", "true")
    from migration_utility.config import get_settings

    get_settings.cache_clear()
    session.add(
        AccountHealthAssessment(
            project_id=project.id,
            entity="account",
            row_count=100,
            cohort_readiness_score=90.0,
            summary={"counts": {"ready": 95, "conditional": 3, "blocked": 2}},
        )
    )
    session.commit()

    plan = WaveOrchestratorService(session).create_plan(
        project,
        name="Gated OK",
        wave_count=2,
        accounts_per_wave=1000,
        require_health_gate=True,
    )
    assert plan.waves_queued == 2


def test_auto_pause_on_high_failure_rate(wave_env):
    session, project = wave_env
    svc = WaveOrchestratorService(session)
    plan = svc.create_plan(
        project,
        name="Pause test",
        wave_count=2,
        accounts_per_wave=100,
        max_failure_pct=5.0,
        run_config={"use_selection": False},
    )
    session.commit()

    run = MigrationRun(
        project_id=project.id,
        name="wave 1",
        status=RunStatus.COMPLETED.value,
        run_config={"wave_plan_id": str(plan.id), "wave_number": 1},
    )
    batch = Batch(batch_number=1, status="completed")
    batch.stats = {"load_summary": {"loaded": 80, "failed": 20}}
    run.batches.append(batch)
    session.add(run)
    session.commit()

    svc.on_run_finished(run)
    session.commit()
    session.refresh(plan)

    assert plan.status == "paused"
    assert plan.waves_failed == 1
    assert "20.0%" in (plan.pause_reason or "")


def test_run_failure_pct_from_batch_stats():
    run = MigrationRun(
        project_id=uuid4(),
        name="x",
        status=RunStatus.COMPLETED.value,
        run_config={},
    )
    batch = Batch(batch_number=1)
    batch.stats = {"load_summary": {"loaded": 90, "failed": 10}}
    run.batches.append(batch)
    assert run_failure_pct(run) == 10.0


def test_pause_cancels_queued_runs(wave_env):
    session, project = wave_env
    svc = WaveOrchestratorService(session)
    plan = svc.create_plan(
        project,
        name="Cancel test",
        wave_count=2,
        accounts_per_wave=100,
    )
    session.commit()
    svc.pause_plan(plan, reason="operator stop")
    session.commit()

    runs = [
        r
        for r in session.query(MigrationRun).all()
        if r.run_config.get("wave_plan_id") == str(plan.id)
    ]
    assert all(r.status == RunStatus.CANCELLED.value for r in runs)
