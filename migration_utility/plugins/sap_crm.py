from __future__ import annotations

from migration_utility.plugins.base import DestinationPlugin
from migration_utility.plugins.schema import DestinationSchema, SchemaField


class SapCrmPlugin(DestinationPlugin):
    id = "sap-crm-v1"
    label = "SAP Customer Master"
    version = "1.0.0"
    adapter_key = "sap"
    transport = "IDoc / BAPI"

    def get_schema(self, entity: str = "account") -> DestinationSchema | None:
        if entity != "account":
            return None
        return DestinationSchema(
            entity="account",
            description="SAP DEBMAS customer master import contract",
            fields=[
                SchemaField(
                    name="KUNNR",
                    data_type="string",
                    required=True,
                    description="Customer number (10 digits)",
                    constraints={"max_length": 10},
                ),
                SchemaField(
                    name="NAME1",
                    data_type="string",
                    required=True,
                    description="Name line 1",
                    constraints={"max_length": 40},
                ),
                SchemaField(name="STATUS", data_type="string", description="Customer status"),
                SchemaField(name="STCD1", data_type="string", description="Tax number 1"),
                SchemaField(name="TELF1", data_type="string", description="Telephone"),
                SchemaField(name="SMTP_ADDR", data_type="string", description="Email address"),
            ],
        )
