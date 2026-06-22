from uuid import uuid4

from migration_utility.connectors.sap import SapClient, SapTargetAdapter
from migration_utility.core.events import RunContext


def _ctx(**config) -> RunContext:
    return RunContext(
        project_id=uuid4(),
        run_id=uuid4(),
        batch_id=uuid4(),
        source_connector_key="staging",
        target_adapter_key="sap",
        config={"entity": "account", **config},
        metadata={"target_system": "sap", "environment": "dev"},
    )


def test_sap_mock_post_customers():
    client = SapClient(mock=True)
    records = [{"KUNNR": "123", "NAME1": "Test Customer", "STATUS": "ACTIVE"}]
    loaded, failed = client.post_customers(records, project_id="proj-1")
    assert len(loaded) == 1
    assert loaded[0]["sapCustomerNumber"] == "0000000123"
    assert loaded[0]["idocType"] == "DEBMAS01"
    assert len(failed) == 0


def test_sap_adapter_maps_kraken_style_fields():
    adapter = SapTargetAdapter(client=SapClient(mock=True))
    records = [
        {
            "accountId": "ACC-100",
            "accountName": "Water Co",
            "accountStatus": "ACTIVE",
        }
    ]
    loaded, failed = adapter.load(records, _ctx())
    assert len(loaded) == 1
    assert loaded[0]["sapCustomerNumber"] == "000ACC-100"


def test_sap_adapter_rejects_missing_customer_number():
    adapter = SapTargetAdapter(client=SapClient(mock=True))
    records = [{"NAME1": "No ID"}]
    loaded, failed = adapter.load(records, _ctx())
    assert len(loaded) == 0
    assert len(failed) >= 1
