from __future__ import annotations

from migration_utility.plugins.base import DestinationPlugin
from migration_utility.plugins.schema import DestinationSchema, SchemaField


class MockDestinationPlugin(DestinationPlugin):
    id = "mock-v1"
    label = "Mock Destination"
    version = "1.0.0"
    adapter_key = "mock"
    transport = "In-memory"

    def get_schema(self, entity: str = "account") -> DestinationSchema | None:
        if entity != "account":
            return None
        return DestinationSchema(
            entity="account",
            description="Generic mock destination for testing",
            fields=[
                SchemaField(name="id", data_type="string", required=True),
                SchemaField(name="name", data_type="string", required=True),
                SchemaField(name="status", data_type="string", required=True),
            ],
        )


class FileExportPlugin(DestinationPlugin):
    id = "file-export-v1"
    label = "JSON File Export"
    version = "1.0.0"
    adapter_key = "file_export"
    transport = "File system"

    def get_schema(self, entity: str = "account") -> DestinationSchema | None:
        if entity != "account":
            return None
        return DestinationSchema(
            entity="account",
            description="Configurable JSON export schema",
            fields=[
                SchemaField(name="id", data_type="string", required=True),
                SchemaField(name="name", data_type="string", required=True),
                SchemaField(name="status", data_type="string", required=True),
                SchemaField(name="metadata", data_type="object"),
            ],
        )
