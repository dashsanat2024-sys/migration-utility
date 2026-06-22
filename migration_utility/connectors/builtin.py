from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from migration_utility.config import get_settings
from migration_utility.connectors.base import SourceConnector, TargetAdapter
from migration_utility.core.events import RunContext


class MockSourceConnector(SourceConnector):
    """Reference source connector for development and tests."""

    key = "mock"

    def extract(self, ctx: RunContext) -> list[dict[str, Any]]:
        count = int(ctx.config.get("mock_record_count", 3))
        return [
            {"id": f"ACC-{i:04d}", "name": f"Account {i}", "status": "active"}
            for i in range(1, count + 1)
        ]


class MockTargetAdapter(TargetAdapter):
    """Reference target adapter — simulates successful load."""

    key = "mock"

    def load(
        self,
        records: list[dict[str, Any]],
        ctx: RunContext,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        fail_ids = set(ctx.config.get("mock_fail_ids", []))
        loaded = [r for r in records if r.get("id") not in fail_ids]
        failed = [r for r in records if r.get("id") in fail_ids]
        return loaded, failed


class FileExportTargetAdapter(TargetAdapter):
    """Writes transformed records to JSON files under the export path."""

    key = "file_export"

    def load(
        self,
        records: list[dict[str, Any]],
        ctx: RunContext,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if not records:
            return [], []

        settings = get_settings()
        export_dir = Path(settings.export_path) / str(ctx.project_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        filename = f"run_{ctx.run_id}_batch_{ctx.batch_id}.json"
        path = export_dir / filename
        path.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")

        loaded = [{**r, "exportPath": str(path)} for r in records]
        return loaded, []
