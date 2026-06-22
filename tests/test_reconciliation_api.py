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


def test_project_reconciliation_summary(client):
    project_resp = client.post(
        "/api/projects",
        json={"name": "Recon Co", "slug": "recon-co", "config": {"mock_record_count": 1}},
    )
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    resp = client.get(f"/api/projects/{project_id}/reconciliation?entity=account")
    assert resp.status_code == 200
    body = resp.json()
    assert body["entity"] == "account"
    assert "counts" in body
    assert body["counts"]["runs_total"] == 0
    assert body["counts"]["staged_total"] == 0


def test_run_reconciliation_after_migration(client):
    project_resp = client.post(
        "/api/projects",
        json={
            "name": "Recon Run",
            "slug": "recon-run",
            "target_adapter_key": "mock",
            "config": {"mock_record_count": 2},
        },
    )
    project_id = project_resp.json()["id"]

    run_resp = client.post(
        f"/api/projects/{project_id}/runs",
        json={"name": "Recon test run", "run_config": {"use_rules": False, "use_selection": False}},
    )
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    recon = client.get(f"/api/runs/{run_id}/reconciliation").json()
    assert recon["run_id"] == run_id
    assert recon["reconciliation_status"] in ("no_candidates", "balanced", "partial", "variance")
    assert "funnel" in recon
    assert "variance" in recon


def test_reconciliation_export(client):
    project_resp = client.post(
        "/api/projects",
        json={"name": "Export Co", "slug": "export-co"},
    )
    project_id = project_resp.json()["id"]

    resp = client.get(f"/api/projects/{project_id}/reconciliation/export?entity=account")
    assert resp.status_code == 200
    body = resp.json()
    assert body["project_slug"] == "export-co"
    assert "summary" in body
    assert "runs" in body
    assert "load_records" in body
