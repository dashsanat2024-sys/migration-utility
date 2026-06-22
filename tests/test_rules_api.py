import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine
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
        yield c, session
    session.close()


def test_seed_and_list_rules(client):
    c, _ = client
    project = c.post("/api/projects", json={"name": "Rules Co", "slug": "rules-co"}).json()
    pid = project["id"]

    seed = c.post(f"/api/projects/{pid}/rules/seed-account")
    assert seed.status_code == 201
    body = seed.json()
    assert body["workflow_state"] == "approved"
    assert len(body["validation_rules"]) >= 2
    assert len(body["field_mappings"]) >= 2

    listed = c.get(f"/api/projects/{pid}/rules?entity=account")
    assert listed.status_code == 200
    assert len(listed.json()) >= 1


def test_workflow_transition(client):
    c, _ = client
    project = c.post("/api/projects", json={"name": "WF Co", "slug": "wf-co"}).json()
    pid = project["id"]

    rs = c.post(
        f"/api/projects/{pid}/rules",
        json={"entity": "account", "name": "Draft rules"},
    ).json()

    c.post(
        f"/api/projects/{pid}/rules/{rs['id']}/workflow",
        json={"workflow_state": "in_review", "role": "mapping_lead", "actor": "test"},
    )
    approved = c.post(
        f"/api/projects/{pid}/rules/{rs['id']}/workflow",
        json={"workflow_state": "approved", "role": "business_analyst", "actor": "test"},
    )
    assert approved.status_code == 200
    assert approved.json()["workflow_state"] == "approved"
