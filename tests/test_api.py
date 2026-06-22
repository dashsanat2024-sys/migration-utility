import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from migration_utility.api.deps import get_db_session
from migration_utility.datastore.base import Base
import migration_utility.datastore.models  # noqa: F401
from migration_utility.main import create_app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # SQLite lacks JSONB — use generic JSON for unit tests
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if column.type.__class__.__name__ == "JSONB":
                column.type = JSON()
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    app = create_app()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as c:
        yield c
    session.close()


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("ok", "degraded")
    assert "mock" in body["connectors"]["sources"]
    targets = body["connectors"]["targets"]
    assert "kraken" in targets
    assert "sap" in targets


def test_kraken_run_persists_load_records(client):
    project_resp = client.post(
        "/api/projects",
        json={
            "name": "Kraken Migration",
            "slug": "kraken-mig",
            "target_system": "kraken",
            "target_adapter_key": "kraken",
            "source_connector_key": "mock",
            "config": {"mock_record_count": 2},
        },
    )
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    seed = client.post(f"/api/projects/{project_id}/rules/seed-account")
    assert seed.status_code == 201

    run_resp = client.post(
        f"/api/projects/{project_id}/runs",
        json={"name": "Kraken Load Run", "run_config": {"use_rules": True, "use_selection": False}},
    )
    assert run_resp.status_code == 201
    run = run_resp.json()
    assert run["status"] == "completed"

    loads = client.get(f"/api/runs/{run['id']}/loads").json()
    assert len(loads) >= 1
    assert all(lr["target_adapter_key"] == "kraken" for lr in loads)

    summary = client.get(f"/api/runs/{run['id']}/loads/summary").json()
    assert summary["total"] == len(loads)
    assert summary["loaded"] >= 1


def test_create_project_and_run(client):
    project_resp = client.post(
        "/api/projects",
        json={
            "name": "Test Water Utility",
            "slug": "test-water",
            "target_system": "kraken",
            "config": {"mock_record_count": 2},
        },
    )
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    run_resp = client.post(
        f"/api/projects/{project_id}/runs",
        json={"name": "Daily Run 1", "run_config": {}},
    )
    assert run_resp.status_code == 201
    run = run_resp.json()
    assert run["status"] == "completed"
    assert len(run["batches"]) == 1
    assert run["batches"][0]["stats"]["success"] is True

    audit_resp = client.get(f"/api/runs/{run['id']}/audit")
    assert audit_resp.status_code == 200
    assert len(audit_resp.json()) >= 4
