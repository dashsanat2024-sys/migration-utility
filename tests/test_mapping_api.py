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
        yield c
    session.close()


def test_mapping_matrix_and_workflow(client):
    c = client
    project = c.post(
        "/api/projects",
        json={"name": "Map Co", "slug": "map-co", "target_system": "kraken"},
    ).json()
    pid = project["id"]

    rs = c.post(f"/api/projects/{pid}/rules/seed-account").json()
    rsid = rs["id"]

    matrix = c.get(f"/api/projects/{pid}/mapping/rules/{rsid}/matrix")
    assert matrix.status_code == 200
    body = matrix.json()
    assert body["coverage"]["source_mapped"] >= 2
    assert len(body["rows"]) >= 3

    opts = c.get(f"/api/projects/{pid}/mapping/rules/{rsid}/workflow/options?role=product_owner")
    assert opts.status_code == 200
    assert "signed_off" in opts.json()["allowed_transitions"] or opts.json()["current_state"] == "approved"

    signed = c.post(
        f"/api/projects/{pid}/rules/{rsid}/workflow",
        json={
            "workflow_state": "signed_off",
            "actor": "Jane PO",
            "role": "product_owner",
            "comment": "Signed off for migration",
        },
    )
    assert signed.status_code == 200
    assert signed.json()["workflow_state"] == "signed_off"

    approvals = c.get(f"/api/projects/{pid}/mapping/rules/{rsid}/approvals")
    assert approvals.status_code == 200
    assert len(approvals.json()) >= 1


def test_tariff_seed_and_load(client):
    c = client
    project = c.post(
        "/api/projects",
        json={"name": "Tariff Co", "slug": "tariff-co", "target_system": "kraken"},
    ).json()
    pid = project["id"]

    seed = c.post(f"/api/projects/{pid}/tariffs/seed")
    assert seed.status_code == 200
    tsid = seed.json()["id"]
    assert len(seed.json()["mappings"]) == 3

    c.post(
        f"/api/projects/{pid}/tariffs/{tsid}/workflow",
        json={"workflow_state": "in_review", "actor": "lead", "role": "mapping_lead"},
    )
    c.post(
        f"/api/projects/{pid}/tariffs/{tsid}/workflow",
        json={"workflow_state": "approved", "actor": "ba", "role": "business_analyst"},
    )
    c.post(
        f"/api/projects/{pid}/tariffs/{tsid}/workflow",
        json={"workflow_state": "signed_off", "actor": "po", "role": "product_owner"},
    )

    load = c.post(f"/api/projects/{pid}/tariffs/{tsid}/load")
    assert load.status_code == 200
    assert load.json()["loaded"] == 3
