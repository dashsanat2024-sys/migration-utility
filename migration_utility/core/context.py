from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageResult:
    stage: str
    success: bool
    records_processed: int = 0
    records_failed: int = 0
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    run_id: str
    success: bool
    stages: list[StageResult] = field(default_factory=list)
    error: str | None = None

    @property
    def total_processed(self) -> int:
        return sum(s.records_processed for s in self.stages)

    @property
    def total_failed(self) -> int:
        return sum(s.records_failed for s in self.stages)
