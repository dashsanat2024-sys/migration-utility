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


def test_schema_entities(client):
    c, _ = client
    resp = c.get("/api/schema/entities")
    assert resp.status_code == 200
    assert "account" in resp.json()


def test_upload_csv_and_stage(client):
    c, _ = client
    project_resp = c.post(
        "/api/projects",
        json={"name": "Water Co", "slug": "water-co", "source_connector_key": "staging"},
    )
    project_id = project_resp.json()["id"]

    csv_data = "id,name,status\nACC-001,Alice,active\nACC-002,Bob,active\n"
    resp = c.post(
        f"/api/projects/{project_id}/ingest/upload",
        data={"entity": "account"},
        files={"file": ("accounts.csv", io.BytesIO(csv_data.encode()), "text/csv")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["staged_count"] == 2
    assert body["status"] == "processed"

    stats = c.get(f"/api/projects/{project_id}/ingest/staging/account/stats")
    assert stats.status_code == 200
    assert stats.json()["row_count"] == 2


def test_staging_connector_run(client):
    c, _ = client
    project_resp = c.post(
        "/api/projects",
        json={
            "name": "Water Co 2",
            "slug": "water-co-2",
            "source_connector_key": "staging",
            "target_adapter_key": "mock",
            "config": {"entity": "account"},
        },
    )
    project_id = project_resp.json()["id"]

    csv_data = "id,name,status\nACC-010,Ted,active\n"
    c.post(
        f"/api/projects/{project_id}/ingest/upload",
        data={"entity": "account"},
        files={"file": ("one.csv", io.BytesIO(csv_data.encode()), "text/csv")},
    )

    run_resp = c.post(
        f"/api/projects/{project_id}/runs",
        json={"name": "Staging run", "run_config": {"entity": "account"}},
    )
    assert run_resp.status_code == 201
    assert run_resp.json()["status"] == "completed"
