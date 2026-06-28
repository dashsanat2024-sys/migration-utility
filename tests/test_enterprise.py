import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from migration_utility.api.deps import get_db_session
from migration_utility.config import get_settings
from migration_utility.datastore.base import Base
import migration_utility.datastore.models  # noqa: F401
from migration_utility.main import create_app
from migration_utility.profiling.service import profile_records


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("AUTH_SECRET", "test-secret")
    get_settings.cache_clear()

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
    get_settings.cache_clear()


def _login(client: TestClient) -> str:
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@arthavi.local", "password": "admin123"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _create_project(client: TestClient) -> str:
    resp = client.post(
        "/api/projects",
        json={
            "name": "Enterprise Test",
            "slug": "enterprise-test",
            "target_system": "kraken",
            "target_adapter_key": "mock",
            "source_connector_key": "mock",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_auth_login_and_me(client):
    token = _login(client)
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "admin@arthavi.local"


def test_auth_status(client):
    resp = client.get("/api/auth/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["auth_enabled"] is True
    assert "runner_mode" in body


def test_profile_records_detects_anomalies():
    records = [
        {"id": "1", "name": "A", "rate": 10},
        {"id": "2", "name": "A", "rate": 10},
        {"id": "3", "name": None, "rate": 10},
    ]
    profile = profile_records(records, entity="account")
    assert profile["row_count"] == 3
    assert profile["summary"]["anomaly_count"] >= 1


def test_ingest_profile_and_exceptions(client):
    project_id = _create_project(client)
    csv = "accountId,name\nACC1,Alice\n,Missing\n"
    upload = client.post(
        f"/api/projects/{project_id}/ingest/upload",
        data={"entity": "account"},
        files={"file": ("accounts.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert upload.status_code == 201
    file_id = upload.json()["id"]

    profile_resp = client.get(f"/api/projects/{project_id}/ingest/files/{file_id}/profile")
    assert profile_resp.status_code == 200
    profile = profile_resp.json()
    assert profile["row_count"] >= 1
    assert "column_stats" in profile

    sync = client.post(f"/api/projects/{project_id}/exceptions/sync-ingest")
    assert sync.status_code == 200
    items = sync.json()
    assert isinstance(items, list)

    listed = client.get(f"/api/projects/{project_id}/exceptions")
    assert listed.status_code == 200


def test_run_progress_endpoint(client):
    project_id = _create_project(client)
    run_resp = client.post(
        f"/api/projects/{project_id}/runs",
        json={
            "name": "Progress test",
            "run_config": {"entity": "account", "use_rules": False, "use_selection": False},
            "batches": [{"batch_number": 1}],
        },
    )
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]
    progress = client.get(f"/api/runs/{run_id}/progress")
    assert progress.status_code == 200
    body = progress.json()
    assert "progress_pct" in body
    assert body["status"] in ("completed", "failed", "running", "queued")
