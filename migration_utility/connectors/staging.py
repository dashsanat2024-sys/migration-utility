from __future__ import annotations

from typing import Any
from uuid import UUID

from migration_utility.connectors.base import SourceConnector
from migration_utility.core.events import RunContext
from migration_utility.datastore.session import get_engine
from migration_utility.ingest.staging import fetch_staged_rows, staging_table_name
from migration_utility.schema.registry import SchemaRegistry
from migration_utility.schema.validation import validate_records


class StagingSourceConnector(SourceConnector):
    """Reads validated rows from auto-generated staging tables."""

    key = "staging"

    def __init__(self, schema_registry: SchemaRegistry) -> None:
        self._schema_registry = schema_registry

    def extract(self, ctx: RunContext) -> list[dict[str, Any]]:
        entity = ctx.config.get("entity", "account")
        project_slug = ctx.metadata.get("project_slug")
        if not project_slug:
            raise ValueError("RunContext.metadata must include project_slug for staging connector")

        table_name = staging_table_name(project_slug, entity)
        batch_id = _optional_uuid(ctx.config.get("filter_batch_id")) or ctx.batch_id
        rows = fetch_staged_rows(
            get_engine(),
            table_name,
            project_id=ctx.project_id,
            source_file_id=_optional_uuid(ctx.config.get("ingest_file_id")),
            run_id=_optional_uuid(ctx.config.get("filter_run_id")),
            batch_id=batch_id,
            status=ctx.config.get("staging_status", "staged"),
        )
        return [_strip_meta(row) for row in rows]

    def validate(
        self,
        records: list[dict[str, Any]],
        ctx: RunContext,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        entity = ctx.config.get("entity", "account")
        schema = self._schema_registry.get(entity)
        if schema is None:
            return records, []

        valid, errors = validate_records(schema, records)
        invalid = [err[1] for err in errors]
        return valid, invalid


def _optional_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    return UUID(str(value))


def _strip_meta(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if not str(k).startswith("_")}
