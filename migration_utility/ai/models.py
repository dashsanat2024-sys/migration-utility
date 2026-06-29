"""Structured AI output models (audit-friendly)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MappingSuggestion(BaseModel):
    destination_field: str
    confidence: float = Field(ge=0.0, le=1.0)
    suggested_transform: str | None = "copy"
    lookup_table: dict[str, str] | None = None
    reasoning: str = ""
    no_match: bool = False


class LookupGap(BaseModel):
    source_field: str
    target_field: str
    enum_name: str | None = None
    unmapped_values: list[str] = Field(default_factory=list)
    proposed_lookup: dict[str, str] = Field(default_factory=dict)
    reasoning: str = ""


class LookupTableSuggestion(BaseModel):
    gaps: list[LookupGap] = Field(default_factory=list)
    summary: str = ""


class ErrorCluster(BaseModel):
    kraken_error_code: str | None = None
    error_class: str = ""
    count: int = 0
    sample_messages: list[str] = Field(default_factory=list)
    likely_root_cause: str = ""
    suggested_mapping_check: str = ""
    owner_role: str | None = None


class ErrorTriageReport(BaseModel):
    total_errors: int = 0
    clusters: list[ErrorCluster] = Field(default_factory=list)
    executive_summary: str = ""
    provider: str = "heuristic"


class AssistantReply(BaseModel):
    answer: str
    references: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
