import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from migration_utility.api.deps import get_db_session
from migration_utility.datastore.base import Base
import migration_utility.datastore.models  # noqa: F401
from migration_utility.main import create_app

SOURCE_CSV = """name,data_type,required
id,string,true
name,string,true
status,string,true
"""

TARGET_CSV = """name,data_type,required
accountId,string,true
accountName,string,true
accountStatus,string,true
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


def test_upload_fields_and_apply_mappings(client):
    project = client.post(
        "/api/projects",
        json={"name": "Field Upload Co", "slug": "field-upload", "target_system": "kraken"},
    ).json()
    pid = project["id"]

    src = client.post(
        f"/api/projects/{pid}/fields/account/source",
        files={"file": ("source_fields.csv", SOURCE_CSV, "text/csv")},
    )
    assert src.status_code == 200
    assert len(src.json()["source_fields"]) == 3

    tgt = client.post(
        f"/api/projects/{pid}/fields/account/target",
        files={"file": ("target_fields.csv", TARGET_CSV, "text/csv")},
    )
    assert tgt.status_code == 200
    assert len(tgt.json()["target_fields"]) == 3

    suggest = client.post(f"/api/projects/{pid}/fields/account/suggest-mappings")
    assert suggest.status_code == 200
    rows = suggest.json()
    assert len(rows) >= 3

    rule_set = client.post(
        f"/api/projects/{pid}/rules",
        json={"entity": "account", "name": "Catalog Rules"},
    ).json()

    mappings = [
        {"source_field": r["source_field"], "target_field": r["target_field"], "transform_type": "copy"}
        for r in rows
        if r.get("source_field") and r.get("target_field")
    ]
    apply = client.post(
        f"/api/projects/{pid}/fields/account/apply-mappings/{rule_set['id']}",
        json={"mappings": mappings},
    )
    assert apply.status_code == 204

    detail = client.get(f"/api/projects/{pid}/rules/{rule_set['id']}").json()
    assert len(detail["field_mappings"]) >= 2

    matrix = client.get(f"/api/projects/{pid}/mapping/rules/{rule_set['id']}/matrix").json()
    assert matrix["field_catalog"]["has_source"] is True
    assert matrix["field_catalog"]["has_target"] is True
    assert matrix["coverage"]["source_total"] == 3


def test_clear_target_fields(client):
    project = client.post(
        "/api/projects",
        json={"name": "Clear Target Co", "slug": "clear-target", "target_system": "kraken"},
    ).json()
    pid = project["id"]

    tgt = client.post(
        f"/api/projects/{pid}/fields/account/target",
        files={"file": ("target_fields.csv", TARGET_CSV, "text/csv")},
    )
    assert tgt.status_code == 200
    assert len(tgt.json()["target_fields"]) == 3

    cleared = client.delete(f"/api/projects/{pid}/fields/account/target")
    assert cleared.status_code == 200
    assert cleared.json()["target_fields"] == []
    assert cleared.json()["target_filename"] is None
