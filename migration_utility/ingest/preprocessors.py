from __future__ import annotations

from typing import Any, Callable

PreProcessorFn = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]


class PreProcessorRegistry:
    """Entity-level hooks to normalize non-compliant extracts before staging."""

    def __init__(self) -> None:
        self._hooks: dict[str, PreProcessorFn] = {}

    def register(self, entity: str, fn: PreProcessorFn) -> None:
        self._hooks[entity] = fn

    def run(self, entity: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        fn = self._hooks.get(entity)
        if fn is None:
            return records
        return fn(records)


def build_default_preprocessors() -> PreProcessorRegistry:
    return PreProcessorRegistry()
