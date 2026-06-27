from __future__ import annotations

from typing import Any

from migration_utility.datastore.models import Project
from migration_utility.plugins.base import DestinationPlugin
from migration_utility.plugins.builtin import FileExportPlugin, MockDestinationPlugin
from migration_utility.plugins.kraken_billing import KrakenBillingPlugin
from migration_utility.plugins.sap_crm import SapCrmPlugin

ADAPTER_TO_DEFAULT_PLUGIN: dict[str, str] = {
    "kraken": "kraken-billing-v3",
    "api_import": "kraken-billing-v3",
    "sap": "sap-crm-v1",
    "file_export": "file-export-v1",
    "mock": "mock-v1",
}


class DestinationPluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, DestinationPlugin] = {}

    def register(self, plugin: DestinationPlugin) -> None:
        self._plugins[plugin.id] = plugin

    def get(self, plugin_id: str) -> DestinationPlugin | None:
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> list[DestinationPlugin]:
        return sorted(self._plugins.values(), key=lambda p: p.label)

    def resolve_for_project(self, project: Project) -> DestinationPlugin:
        plugin_id = resolve_plugin_id(project)
        plugin = self.get(plugin_id)
        if not plugin:
            raise KeyError(f"Unknown destination plugin: {plugin_id!r}")
        return plugin


def resolve_plugin_id(project: Project) -> str:
    config = project.config or {}
    explicit = config.get("destination_plugin_id")
    if explicit:
        return str(explicit)
    adapter = project.target_adapter_key or "mock"
    return ADAPTER_TO_DEFAULT_PLUGIN.get(adapter, "mock-v1")


def build_default_plugin_registry() -> DestinationPluginRegistry:
    registry = DestinationPluginRegistry()
    registry.register(KrakenBillingPlugin())
    registry.register(SapCrmPlugin())
    registry.register(FileExportPlugin())
    registry.register(MockDestinationPlugin())
    return registry
