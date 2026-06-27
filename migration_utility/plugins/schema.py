from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SchemaField(BaseModel):
    """Single field in a destination plugin's published contract."""

    name: str
    data_type: str = "string"
    required: bool = False
    description: str = ""
    constraints: dict[str, Any] = Field(default_factory=dict)


class DestinationSchema(BaseModel):
    """Schema contract published by a destination plugin for one entity."""

    entity: str
    description: str = ""
    fields: list[SchemaField] = Field(default_factory=list)

    def required_fields(self) -> list[SchemaField]:
        return [f for f in self.fields if f.required]

    def optional_fields(self) -> list[SchemaField]:
        return [f for f in self.fields if not f.required]

    def to_catalog_fields(self) -> list[dict[str, Any]]:
        return [f.model_dump() for f in self.fields]
