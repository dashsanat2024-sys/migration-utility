from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ValidationRuleType(StrEnum):
    REQUIRED = "required"
    FORMAT = "format"
    IN_LIST = "in_list"
    RANGE = "range"
    CROSS_FIELD = "cross_field"
    UNIQUE = "unique"


class TransformType(StrEnum):
    COPY = "copy"
    DEFAULT = "default"
    CONCAT = "concat"
    LOOKUP = "lookup"
    CONDITIONAL = "conditional"
    CONSTANT = "constant"
    UPPERCASE = "uppercase"
    LOWERCASE = "lowercase"
    DATE_FORMAT = "date_format"
    PAD_LEFT = "pad_left"
    REGEX_REPLACE = "regex_replace"


@dataclass
class ValidationRuleDef:
    id: str
    name: str
    rule_type: str
    field_name: str | None
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class FieldMappingDef:
    id: str
    source_field: str | None
    target_field: str
    transform_type: str
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    sort_order: int = 0


@dataclass
class LoadedRuleSet:
    id: str
    project_id: str
    entity: str
    name: str
    version: int
    workflow_state: str
    validation_rules: list[ValidationRuleDef] = field(default_factory=list)
    field_mappings: list[FieldMappingDef] = field(default_factory=list)

    @property
    def is_runnable(self) -> bool:
        return self.workflow_state in ("approved", "signed_off")
