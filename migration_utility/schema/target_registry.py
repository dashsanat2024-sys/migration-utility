from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TargetField:
    name: str
    data_type: str
    required: bool = False
    description: str = ""


@dataclass
class TargetEntity:
    name: str
    fields: list[TargetField] = field(default_factory=list)
    description: str = ""


class TargetSchemaRegistry:
    """Target-system field catalog for the mapping matrix UI."""

    def __init__(self) -> None:
        self._by_system: dict[str, dict[str, TargetEntity]] = {}

    def register(self, target_system: str, entity: TargetEntity) -> None:
        self._by_system.setdefault(target_system.lower(), {})[entity.name] = entity

    def get(self, target_system: str, entity: str) -> TargetEntity | None:
        return self._by_system.get(target_system.lower(), {}).get(entity)

    def list_entities(self, target_system: str) -> list[str]:
        return sorted(self._by_system.get(target_system.lower(), {}))


def build_default_target_registry() -> TargetSchemaRegistry:
    registry = TargetSchemaRegistry()
    registry.register(
        "kraken",
        TargetEntity(
            name="account",
            description="Kraken account migration API payload",
            fields=[
                TargetField("accountId", "string", required=True, description="Unique account identifier"),
                TargetField("accountName", "string", required=True),
                TargetField("accountStatus", "string", required=True, description="ACTIVE | INACTIVE"),
            ],
        ),
    )
    registry.register(
        "generic",
        TargetEntity(
            name="account",
            fields=[
                TargetField("id", "string", required=True),
                TargetField("name", "string", required=True),
                TargetField("status", "string", required=True),
            ],
        ),
    )
    registry.register(
        "sap",
        TargetEntity(
            name="account",
            description="SAP customer master (DEBMAS)",
            fields=[
                TargetField("KUNNR", "string", required=True, description="Customer number"),
                TargetField("NAME1", "string", required=True, description="Name line 1"),
                TargetField("STATUS", "string", required=False, description="Customer status"),
            ],
        ),
    )
    registry.register(
        "kraken",
        TargetEntity(
            name="tariff",
            description="Kraken product/tariff import API",
            fields=[
                TargetField("productCode", "string", required=True),
                TargetField("displayName", "string", required=False),
            ],
        ),
    )
    return registry
