from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass
class PipelineEvent:
    """Emitted as each pipeline stage completes or fails."""

    stage: str
    run_id: UUID
    batch_id: UUID | None
    status: str  # "started" | "completed" | "failed"
    message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventBus:
    """Simple in-process event bus for pipeline observability."""

    def __init__(self) -> None:
        self._handlers: list = []

    def subscribe(self, handler) -> None:
        self._handlers.append(handler)

    def publish(self, event: PipelineEvent) -> None:
        for handler in self._handlers:
            handler(event)


@dataclass
class RunContext:
    """Runtime context passed through every pipeline stage."""

    project_id: UUID
    run_id: UUID
    batch_id: UUID | None
    source_connector_key: str
    target_adapter_key: str
    config: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
