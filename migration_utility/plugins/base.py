from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from migration_utility.plugins.schema import DestinationSchema


class DestinationPlugin(ABC):
    """Destination adapter that owns and publishes its field schema contract."""

    id: str
    label: str
    version: str
    adapter_key: str
    transport: str = "REST API"

    @abstractmethod
    def get_schema(self, entity: str = "account") -> DestinationSchema | None:
        """Return the published schema for an entity, or None if unsupported."""

    def validate_payload(self, entity: str, payload: dict[str, Any]) -> list[str]:
        """Validate a single record against the plugin schema. Returns error messages."""
        schema = self.get_schema(entity)
        if not schema:
            return [f"Entity {entity!r} not supported by plugin {self.id!r}"]
        errors: list[str] = []
        for field in schema.fields:
            if not field.required:
                continue
            value = payload.get(field.name)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Missing required field: {field.name}")
        return errors
