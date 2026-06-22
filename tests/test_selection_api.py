import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from migration_utility.api.deps import get_db_session
from migration_utility.datastore.base import Base
import migration_utility.datastore.models  # noqa: F401
from migration_utility.ingest.service import IngestService
from migration_utility.main import create_app


@pytest.fixture()
def client(monkeypatch):
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

    def ingest_service_factory(db, schema_registry, preprocessors):
        return IngestService(db, schema_registry, preprocessors, engine=engine)

    monkeypatch.setattr("migration_utility.api.routes.ingest._ingest_service", ingest_service_factory)
    monkeypatch.setattr("migration_utility.api.routes.ingest.get_engine", lambda: engine)
    monkeypatch.setattr("migration_utility.connectors.staging.get_engine", lambda: engine)
    monkeypatch.setattr("migration_utility.selection.service.get_engine", lambda: engine)

    app = create_app()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db_session] = override_get_db
    with TestClient(app) as c:
        yield c, session
    session.close()


def test_seed_and_list_profiles(client):
    c, _ = client
    project_resp = c.post(
        "/api/projects",
        json={"name": "Sel Co", "slug": "sel-co", "source_connector_key": "staging"},
    )
    project_id = project_resp.json()["id"]

    seed = c.post(f"/api/projects/{project_id}/selection/profiles/seed-account")
    assert seed.status_code == 200
    body = seed.json()
    assert body["name"] == "Active Accounts"
    assert len(body["criteria"]) == 1

    listed = c.get(f"/api/projects/{project_id}/selection/profiles")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_preview_and_selection_run(client):
    c, _ = client
    project_resp = c.post(
        "/api/projects",
        json={
            "name": "Sel Co 2",
            "slug": "sel-co-2",
            "source_connector_key": "staging",
            "target_adapter_key": "mock",
        },
    )
    project_id = project_resp.json()["id"]
    c.post(f"/api/projects/{project_id}/selection/profiles/seed-account")

    csv_data = (
        "id,name,status\n"
        "ACC-001,Alice,active\n"
        "ACC-002,Bob,inactive\n"
        "ACC-003,Carol,active\n"
    )
    c.post(
        f"/api/projects/{project_id}/ingest/upload",
        data={"entity": "account"},
        files={"file": ("accounts.csv", io.BytesIO(csv_data.encode()), "text/csv")},
    )

    preview = c.post(
        f"/api/projects/{project_id}/selection/preview",
        json={"entity": "account"},
    )
    assert preview.status_code == 200
    assert preview.json()["selected_count"] == 2
    assert preview.json()["excluded_count"] == 1

    run_resp = c.post(
        f"/api/projects/{project_id}/runs",
        json={
            "name": "Selection run",
            "run_config": {"entity": "account", "use_selection": True, "use_rules": False},
        },
    )
    assert run_resp.status_code == 201
    run = run_resp.json()
    assert run["status"] == "completed"
    assert run["batches"][0]["stats"]["candidate_count"] == 2

    candidates = c.get(f"/api/runs/{run['id']}/candidates")
    assert candidates.status_code == 200
    assert len(candidates.json()) == 2
    assert {item["external_id"] for item in candidates.json()} == {"ACC-001", "ACC-003"}


def test_selection_run_with_duplicate_staging_rows(client):
    c, _ = client
    project_resp = c.post(
        "/api/projects",
        json={
            "name": "Dup Co",
            "slug": "dup-co",
            "source_connector_key": "staging",
            "target_adapter_key": "mock",
        },
    )
    project_id = project_resp.json()["id"]
    c.post(f"/api/projects/{project_id}/selection/profiles/seed-account")

    csv_data = "id,name,status\nACC-001,Alice,active\n"
    for name in ("first.csv", "second.csv"):
        c.post(
            f"/api/projects/{project_id}/ingest/upload",
            data={"entity": "account"},
            files={"file": (name, io.BytesIO(csv_data.encode()), "text/csv")},
        )

    run_resp = c.post(
        f"/api/projects/{project_id}/runs",
        json={
            "name": "Dup run",
            "run_config": {"entity": "account", "use_selection": True, "use_rules": False},
        },
    )
    assert run_resp.status_code == 201
    run = run_resp.json()
    assert run["status"] == "completed"
    assert run["batches"][0]["stats"]["candidate_count"] == 1

    candidates = c.get(f"/api/runs/{run['id']}/candidates")
    assert len(candidates.json()) == 1


def test_toggle_criterion(client):
    c, _ = client
    project_resp = c.post(
        "/api/projects",
        json={"name": "Toggle Co", "slug": "toggle-co", "source_connector_key": "staging"},
    )
    project_id = project_resp.json()["id"]
    seed = c.post(f"/api/projects/{project_id}/selection/profiles/seed-account").json()
    criterion_id = seed["criteria"][0]["id"]
    profile_id = seed["id"]

    toggled = c.patch(
        f"/api/projects/{project_id}/selection/profiles/{profile_id}/criteria/{criterion_id}",
        json={"enabled": False},
    )
    assert toggled.status_code == 200
    assert toggled.json()["enabled"] is False
