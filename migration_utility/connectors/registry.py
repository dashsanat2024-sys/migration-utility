from __future__ import annotations

from migration_utility.connectors.base import SourceConnector, TargetAdapter
from migration_utility.connectors.builtin import (
    FileExportTargetAdapter,
    MockSourceConnector,
    MockTargetAdapter,
)
from migration_utility.connectors.kraken import KrakenTargetAdapter
from migration_utility.connectors.sap import SapTargetAdapter
from migration_utility.connectors.staging import StagingSourceConnector
from migration_utility.schema.registry import SchemaRegistry, build_default_schema_registry


class ConnectorRegistry:
    """Registry for source connectors and target adapters."""

    def __init__(self) -> None:
        self._sources: dict[str, SourceConnector] = {}
        self._targets: dict[str, TargetAdapter] = {}

    def register_source(self, connector: SourceConnector) -> None:
        self._sources[connector.key] = connector

    def register_target(self, adapter: TargetAdapter) -> None:
        self._targets[adapter.key] = adapter

    def get_source(self, key: str) -> SourceConnector:
        if key not in self._sources:
            raise KeyError(f"Unknown source connector: {key!r}")
        return self._sources[key]

    def get_target(self, key: str) -> TargetAdapter:
        if key not in self._targets:
            raise KeyError(f"Unknown target adapter: {key!r}")
        return self._targets[key]

    def list_sources(self) -> list[str]:
        return sorted(self._sources)

    def list_targets(self) -> list[str]:
        return sorted(self._targets)


def build_default_registry(schema_registry: SchemaRegistry | None = None) -> ConnectorRegistry:
    registry = ConnectorRegistry()
    registry.register_source(MockSourceConnector())
    schema_registry = schema_registry or build_default_schema_registry()
    registry.register_source(StagingSourceConnector(schema_registry))
    registry.register_target(MockTargetAdapter())
    registry.register_target(FileExportTargetAdapter())
    registry.register_target(KrakenTargetAdapter())
    registry.register_target(SapTargetAdapter())
    return registry
