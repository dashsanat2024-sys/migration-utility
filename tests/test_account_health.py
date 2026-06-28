"""Tests for Kraken error catalog and account health assessment."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from migration_utility.api.deps import get_db_session
from migration_utility.datastore.base import Base
import migration_utility.datastore.models  # noqa: F401
from migration_utility.main import create_app
from migration_utility.kraken.errors.catalog import get_kraken_error_catalog
from migration_utility.kraken.errors.classifier import classify_kraken_response, classify_validation_finding
from migration_utility.account_health.checks import DEFAULT_HEALTH_CHECKS


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


def test_catalog_indexes_hundreds_of_codes():
    catalog = get_kraken_error_catalog()
    assert catalog.total_codes == 920
    assert catalog.detailed_count == 57


def test_catalog_get_known_code():
    entry = get_kraken_error_catalog().get("KT-CT-10006")
    assert entry is not None
    assert entry["message"] == "Account not found."
    assert entry["has_detail"] is True


def test_catalog_indexed_code_in_range():
    entry = get_kraken_error_catalog().get("KT-CT-10950")
    assert entry is not None
    assert entry["category"] == "account_business_migration"
    assert entry["indexed_only"] is True


def test_classify_validation_finding_pending_payment():
    result = classify_validation_finding("pending_payment", "Pending payment")
    assert result["root_cause_category"] == "operational_blocker"
    assert result["owner_role"] == "billing_ops"
    assert result["primary_kraken_code"]


def test_classify_kraken_response_by_message():
    result = classify_kraken_response("Party is already under contract.")
    assert result["primary_kraken_code"] == "KT-CT-10001"
    assert result["root_cause_category"] == "kraken_validation"


def test_classify_kraken_response_by_code_in_text():
    result = classify_kraken_response("Error KT-CT-10021: Business not found.")
    assert result["primary_kraken_code"] == "KT-CT-10021"


def test_health_check_missing_account():
    check = next(c for c in DEFAULT_HEALTH_CHECKS if c.id == "missing_account_number")
    msg = check.evaluate({}, {})
    assert msg is not None


def test_health_check_operational_blocker():
    check = next(c for c in DEFAULT_HEALTH_CHECKS if c.id == "pending_payment")
    msg = check.evaluate({"pendingPayment": "Y"}, {})
    assert msg is not None


def test_account_health_assess_empty(client):
    project_resp = client.post(
        "/api/projects",
        json={
            "name": "Health Test",
            "slug": "health-test",
            "target_system": "kraken",
            "target_adapter_key": "mock",
            "source_connector_key": "mock",
        },
    )
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    resp = client.post(
        f"/api/projects/{project_id}/account-health/assess",
        json={"entity": "account"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["row_count"] == 0
    assert body["cohort_readiness_score"] == 0.0


def test_kraken_error_api_summary(client):
    resp = client.get("/api/kraken/error-codes/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_codes"] == 920


def test_migration_testing_plan(client):
    project_resp = client.post(
        "/api/projects",
        json={
            "name": "Testing Plan",
            "slug": "testing-plan",
            "target_system": "kraken",
            "target_adapter_key": "mock",
            "source_connector_key": "mock",
        },
    )
    project_id = project_resp.json()["id"]
    resp = client.get(f"/api/projects/{project_id}/migration-testing/plan")
    assert resp.status_code == 200
    assert any(p["id"] == "dress_rehearsal" for p in resp.json()["phases"])
