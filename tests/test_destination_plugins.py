import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import migration_utility.datastore.models  # noqa: F401
from migration_utility.api.deps import get_db_session
from migration_utility.datastore.base import Base
from migration_utility.main import create_app

SOURCE_CSV = """name,data_type,required
CUST_ACCOUNT_NO,string,true
NM_FOR_INDIVIDUAL,string,true
CUST_TYPE_FLAG,string,true
STEPPED_RATE_FLAG,bool,true
AD_EMAIL,string,false
"""


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


def test_list_destination_plugins(client):
    resp = client.get("/api/destination/plugins")
    assert resp.status_code == 200
    ids = {p["id"] for p in resp.json()}
    assert "kraken-billing-v3" in ids
    assert "sap-crm-v1" in ids


def test_project_destination_schema_kraken(client):
    project = client.post(
        "/api/projects",
        json={
            "name": "Plugin Schema Co",
            "slug": "plugin-schema",
            "target_adapter_key": "kraken",
        },
    ).json()
    pid = project["id"]

    plugin = client.get(f"/api/projects/{pid}/destination/plugin").json()
    assert plugin["id"] == "kraken-billing-v3"

    schema = client.get(f"/api/projects/{pid}/destination/schema?entity=account").json()
    assert schema["entity"] == "account"
    assert len(schema["fields"]) >= 30
    required = [f["name"] for f in schema["fields"] if f["required"]]
    assert "number" in required
    assert "accountType" in required
    assert "isOnSteppedTariff" in required
    assert "billingOptions.isFixed" in required
    provenance = [f["name"] for f in schema["fields"] if f.get("constraints", {}).get("migration_provenance")]
    assert "migrationSource" in provenance
    assert "isMigrated" in provenance
    assert "urn" in provenance


def test_suggest_mappings_from_plugin_schema(client):
    project = client.post(
        "/api/projects",
        json={"name": "Suggest Plugin", "slug": "suggest-plugin", "target_adapter_key": "kraken"},
    ).json()
    pid = project["id"]

    src = client.post(
        f"/api/projects/{pid}/fields/account/source",
        files={"file": ("source_fields.csv", SOURCE_CSV, "text/csv")},
    )
    assert src.status_code == 200

    suggest = client.post(
        f"/api/projects/{pid}/fields/account/suggest-mappings?destination_first=true"
    )
    assert suggest.status_code == 200
    rows = suggest.json()
    assert len(rows) >= 10
    dest_rows = [r for r in rows if r.get("target_field")]
    assert all("target_required" in r for r in dest_rows)
    assert any(r["target_field"] == "number" for r in dest_rows)
    migration_row = next((r for r in dest_rows if r["target_field"] == "migrationSource"), None)
    assert migration_row is not None
    assert migration_row.get("target_constraints", {}).get("migration_provenance") is True


def test_swap_destination_plugin(client):
    project = client.post(
        "/api/projects",
        json={"name": "Swap Plugin", "slug": "swap-plugin", "target_adapter_key": "kraken"},
    ).json()
    pid = project["id"]

    swapped = client.post(
        f"/api/projects/{pid}/destination/swap",
        json={"plugin_id": "sap-crm-v1", "confirm_orphan": True},
    )
    assert swapped.status_code == 200
    assert swapped.json()["id"] == "sap-crm-v1"

    schema = client.get(f"/api/projects/{pid}/destination/schema").json()
    assert any(f["name"] == "KUNNR" for f in schema["fields"])
