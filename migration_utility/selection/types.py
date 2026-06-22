from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID


class SelectionOperator(StrEnum):
    EQ = "eq"
    NE = "ne"
    IN = "in"
    NOT_IN = "not_in"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class SelectionLogic(StrEnum):
    AND = "and"
    OR = "or"


@dataclass
class CriterionDef:
    id: UUID | None
    field_name: str
    operator: str
    value: Any = None
    enabled: bool = True
    sort_order: int = 0


@dataclass
class LoadedSelectionProfile:
    id: UUID
    name: str
    entity: str
    logic: str
    max_candidates: int | None
    criteria: list[CriterionDef] = field(default_factory=list)
