from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from migration_utility.core.enums import IngestFileStatus
from migration_utility.datastore.models import IngestError, IngestFile, Project
from migration_utility.datastore.session import get_engine
from migration_utility.ingest.landing import save_upload
from migration_utility.ingest.parsers import ParseError, detect_format, parse_file
from migration_utility.ingest.preprocessors import PreProcessorRegistry
from migration_utility.ingest.staging import (
    ensure_staging_table,
    insert_staged_rows,
    staging_table_name,
)
from migration_utility.schema.registry import SchemaRegistry
from migration_utility.schema.validation import validate_records


class IngestService:
    """Parse landing-zone files, validate against schema, and load into staging tables."""

    def __init__(
        self,
        db: Session,
        schema_registry: SchemaRegistry,
        preprocessors: PreProcessorRegistry | None = None,
        engine: Engine | None = None,
    ) -> None:
        self._db = db
        self._schema_registry = schema_registry
        self._preprocessors = preprocessors or PreProcessorRegistry()
        self._engine_override = engine

    @property
    def engine(self) -> Engine:
        return self._engine_override or get_engine()

    def register_upload(
        self,
        project: Project,
        *,
        entity: str,
        original_filename: str,
        temp_path: Path,
        content_type: str | None = None,
    ) -> IngestFile:
        if not self._schema_registry.get(entity):
            raise ValueError(f"Unknown schema entity: {entity!r}")

        file_format = detect_format(original_filename, content_type)
        landing_path = save_upload(project.slug, original_filename, temp_path)

        ingest_file = IngestFile(
            project_id=project.id,
            entity=entity,
            original_filename=original_filename,
            landing_path=str(landing_path),
            file_format=file_format,
            status=IngestFileStatus.PENDING.value,
        )
        self._db.add(ingest_file)
        self._db.commit()
        self._db.refresh(ingest_file)
        return ingest_file

    def process_file(
        self,
        ingest_file: IngestFile,
        project: Project,
        *,
        run_id: UUID | None = None,
        batch_id: UUID | None = None,
    ) -> IngestFile:
        entity_schema = self._schema_registry.get(ingest_file.entity)
        if entity_schema is None:
            raise ValueError(f"Unknown schema entity: {ingest_file.entity!r}")

        ingest_file.status = IngestFileStatus.PROCESSING.value
        self._db.commit()

        try:
            records = parse_file(Path(ingest_file.landing_path), ingest_file.file_format)

            records = self._preprocessors.run(ingest_file.entity, records)
            valid, errors = validate_records(entity_schema, records)

            table_name = staging_table_name(project.slug, ingest_file.entity)
            table = ensure_staging_table(self.engine, table_name, entity_schema)

            error_rows = {row_num for row_num, _, _ in errors}
            valid_row_numbers = [
                idx for idx in range(1, len(records) + 1) if idx not in error_rows
            ]

            staged = insert_staged_rows(
                self._db.connection(),
                table,
                project_id=project.id,
                source_file_id=ingest_file.id,
                rows=valid,
                row_numbers=valid_row_numbers,
                run_id=run_id,
                batch_id=batch_id,
            )

            for row_number, raw, reason in errors:
                self._db.add(
                    IngestError(
                        project_id=project.id,
                        ingest_file_id=ingest_file.id,
                        entity=ingest_file.entity,
                        row_number=row_number,
                        raw_payload=raw,
                        error_reason=reason,
                    )
                )

            ingest_file.staging_table = table_name
            ingest_file.staged_count = staged
            ingest_file.error_count = len(errors)
            ingest_file.total_rows = len(records)
            ingest_file.status = IngestFileStatus.PROCESSED.value
            ingest_file.message = f"Staged {staged} row(s), {len(errors)} error(s)"
        except (ParseError, ValueError, OSError) as exc:
            ingest_file.status = IngestFileStatus.FAILED.value
            ingest_file.message = str(exc)

        self._db.commit()
        self._db.refresh(ingest_file)
        return ingest_file

    def reprocess_error(self, error: IngestError, project: Project) -> IngestError:
        if error.resolved:
            return error

        entity_schema = self._schema_registry.get(error.entity)
        if entity_schema is None:
            raise ValueError(f"Unknown schema entity: {error.entity!r}")

        valid, errors = validate_records(entity_schema, [error.raw_payload])
        if errors:
            error.error_reason = errors[0][2]
            self._db.commit()
            return error

        ingest_file = self._db.get(IngestFile, error.ingest_file_id)
        if ingest_file is None or not ingest_file.staging_table:
            raise ValueError("Source ingest file or staging table not found")

        table = ensure_staging_table(self.engine, ingest_file.staging_table, entity_schema)
        insert_staged_rows(
            self._db.connection(),
            table,
            project_id=project.id,
            source_file_id=ingest_file.id,
            rows=valid,
            row_numbers=[error.row_number],
        )

        error.resolved = True
        if ingest_file:
            ingest_file.staged_count += 1
            ingest_file.error_count = max(0, ingest_file.error_count - 1)
        self._db.commit()
        self._db.refresh(error)
        return error
