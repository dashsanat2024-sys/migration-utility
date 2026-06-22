from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from migration_utility.core.events import RunContext


class SourceConnector(ABC):
    """Pluggable source — extract, validate, transform from legacy systems."""

    key: str = "base"

    @abstractmethod
    def extract(self, ctx: RunContext) -> list[dict[str, Any]]:
        """Pull raw records for the current run/batch."""

    def validate(
        self,
        records: list[dict[str, Any]],
        ctx: RunContext,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return (valid, invalid) record lists. Override for custom rules."""
        return records, []

    def transform(
        self,
        records: list[dict[str, Any]],
        ctx: RunContext,
    ) -> list[dict[str, Any]]:
        """Map source records to target-ready payloads. Pass-through by default."""
        return records


class TargetAdapter(ABC):
    """Pluggable target — load transformed records into destination systems."""

    key: str = "base"

    @abstractmethod
    def load(
        self,
        records: list[dict[str, Any]],
        ctx: RunContext,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return (loaded, failed) record lists."""

    def validate_target_payload(
        self,
        records: list[dict[str, Any]],
        ctx: RunContext,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Optional pre-load validation against target schema."""
        return records, []
