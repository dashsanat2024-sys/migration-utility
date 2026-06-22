from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SchemaField:
    name: str
    data_type: str
    required: bool = False
    description: str = ""
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class SchemaEntity:
    name: str
    fields: list[SchemaField] = field(default_factory=list)
    description: str = ""


class SchemaRegistry:
    """Canonical extract schema registry (Phase 0 — in-memory)."""

    def __init__(self) -> None:
        self._entities: dict[str, SchemaEntity] = {}

    def register(self, entity: SchemaEntity) -> None:
        self._entities[entity.name] = entity

    def get(self, name: str) -> SchemaEntity | None:
        return self._entities.get(name)

    def list_entities(self) -> list[str]:
        return sorted(self._entities)

    def to_dict(self) -> dict[str, Any]:
        return {
            name: {
                "description": entity.description,
                "fields": [
                    {
                        "name": f.name,
                        "data_type": f.data_type,
                        "required": f.required,
                        "description": f.description,
                    }
                    for f in entity.fields
                ],
            }
            for name, entity in self._entities.items()
        }


def build_default_schema_registry() -> SchemaRegistry:
    registry = SchemaRegistry()
    registry.register(
        SchemaEntity(
            name="account",
            description="Standard account entity for CIS/billing migrations",
            fields=[
                SchemaField("id", "string", required=True),
                SchemaField("name", "string", required=True),
                SchemaField("status", "string", required=True),
            ],
        )
    )
    return registry
