from uuid import uuid4

from migration_utility.connectors.kraken import KrakenClient, KrakenTargetAdapter
from migration_utility.core.events import RunContext


def _ctx(**config) -> RunContext:
    return RunContext(
        project_id=uuid4(),
        run_id=uuid4(),
        batch_id=uuid4(),
        source_connector_key="staging",
        target_adapter_key="kraken",
        config={"entity": "account", **config},
        metadata={"target_system": "kraken", "environment": "dev"},
    )


def test_kraken_mock_import_accounts():
    client = KrakenClient(mock=True)
    records = [
        {"accountId": "ACC-001", "accountName": "Test Co", "accountStatus": "ACTIVE"},
        {"accountName": "Missing ID"},
    ]
    loaded, failed = client.import_accounts(records, project_id="proj-1", environment="dev")
    assert len(loaded) == 1
    assert loaded[0]["krakenAccountId"] == "KRA-ACC-001"
    assert loaded[0]["importStatus"] == "accepted"
    assert len(failed) == 1


def test_kraken_adapter_validates_and_loads():
    adapter = KrakenTargetAdapter(client=KrakenClient(mock=True))
    records = [
        {"accountId": "ACC-002", "accountName": "Acme", "accountStatus": "ACTIVE"},
        {"accountId": "ACC-003", "accountName": "Beta", "accountStatus": "INACTIVE"},
    ]
    loaded, failed = adapter.load(records, _ctx())
    assert len(loaded) == 2
    assert len(failed) == 0
    assert all(r["importStatus"] == "accepted" for r in loaded)


def test_kraken_adapter_rejects_missing_required_fields():
    adapter = KrakenTargetAdapter(client=KrakenClient(mock=True))
    records = [{"accountId": "ACC-004", "accountName": "Partial"}]
    loaded, failed = adapter.load(records, _ctx())
    assert len(loaded) == 0
    assert len(failed) == 1
    assert "_validation_errors" in failed[0]
