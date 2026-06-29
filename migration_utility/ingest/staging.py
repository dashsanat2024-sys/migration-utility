from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    Uuid,
    inspect,
    text,
)
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.types import TypeEngine

from migration_utility.schema.registry import SchemaEntity

_metadata = MetaData()
_TYPE_MAP: dict[str, TypeEngine] = {
    "string": Text(),
    "integer": BigInteger(),
    "decimal": Numeric(18, 4),
    "boolean": Boolean(),
    "date": Date(),
    "datetime": DateTime(timezone=True),
}


def staging_table_name(project_slug: str, entity: str) -> str:
    raw = f"stg_{project_slug}_{entity}".lower().replace("-", "_")
    safe = re.sub(r"[^a-z0-9_]", "_", raw)
    return safe[:63]


def _uuid_column(name: str, *, primary_key: bool = False, nullable: bool = True) -> Column:
    return Column(name, Uuid(as_uuid=True), primary_key=primary_key, nullable=nullable)


def ensure_staging_table(engine: Engine, table_name: str, entity: SchemaEntity) -> Table:
    inspector = inspect(engine)
    if table_name in _metadata.tables:
        return _metadata.tables[table_name]
    if table_name in inspector.get_table_names():
        table = Table(table_name, _metadata, autoload_with=engine)
        ensure_staging_indexes(engine, table_name)
        return table

    columns: list[Column] = [
        _uuid_column("_row_id", primary_key=True),
        _uuid_column("_project_id", nullable=False),
        _uuid_column("_run_id", nullable=True),
        _uuid_column("_batch_id", nullable=True),
        _uuid_column("_source_file_id", nullable=True),
        Column("_row_number", BigInteger(), nullable=False),
        Column("_status", String(32), nullable=False, server_default="staged"),
        Column("_ingested_at", DateTime(timezone=True), nullable=False),
    ]
    for field in entity.fields:
        col_type = _TYPE_MAP.get(field.data_type.lower(), Text())
        columns.append(Column(field.name, col_type, nullable=not field.required))

    table = Table(table_name, _metadata, *columns)
    table.create(bind=engine, checkfirst=True)
    ensure_staging_indexes(engine, table_name)
    return table


def ensure_staging_indexes(engine: Engine, table_name: str) -> None:
    """Create indexes for chunked batch reads (idempotent)."""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return

    existing_names = {idx["name"] for idx in inspector.get_indexes(table_name)}

    specs = [
        (
            _staging_index_name(table_name, "proj_status_batch"),
            "(_project_id, _status, _batch_id)",
        ),
        (
            _staging_index_name(table_name, "proj_status_batch_row"),
            "(_project_id, _status, _batch_id, _row_number)",
        ),
    ]

    with engine.begin() as conn:
        for index_name, columns in specs:
            if index_name in existing_names:
                continue
            conn.execute(
                text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} {columns}")
            )


def _staging_index_name(table_name: str, suffix: str) -> str:
    raw = f"ix_{table_name}_{suffix}".lower().replace("-", "_")
    safe = re.sub(r"[^a-z0-9_]", "_", raw)
    return safe[:63]


def insert_staged_rows(
    conn: Connection,
    table: Table,
    *,
    project_id: uuid.UUID,
    source_file_id: uuid.UUID,
    rows: list[dict[str, Any]],
    row_numbers: list[int],
    run_id: uuid.UUID | None = None,
    batch_id: uuid.UUID | None = None,
) -> int:
    if not rows:
        return 0

    now = datetime.now(timezone.utc)
    payload = []
    for row_number, row in zip(row_numbers, rows, strict=True):
        record: dict[str, Any] = {
            "_row_id": uuid.uuid4(),
            "_project_id": project_id,
            "_run_id": run_id,
            "_batch_id": batch_id,
            "_source_file_id": source_file_id,
            "_row_number": row_number,
            "_status": "staged",
            "_ingested_at": now,
        }
        for col in table.columns:
            name = col.name
            if name.startswith("_"):
                continue
            record[name] = _serialize_value(row.get(name))
        payload.append(record)

    conn.execute(table.insert(), payload)
    return len(payload)


def _bind(value: uuid.UUID | None, dialect_name: str) -> str | None:
    if value is None:
        return None
    if dialect_name == "sqlite":
        return value.hex
    return str(value)


def fetch_staged_rows(
    engine: Engine,
    table_name: str,
    *,
    project_id: uuid.UUID,
    source_file_id: uuid.UUID | None = None,
    run_id: uuid.UUID | None = None,
    batch_id: uuid.UUID | None = None,
    status: str = "staged",
    unassigned_only: bool = False,
    after_row_number: int = 0,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return []

    dialect_name = engine.dialect.name
    clauses = ["_project_id = :project_id", "_status = :status"]
    params: dict[str, Any] = {
        "project_id": _bind(project_id, dialect_name),
        "status": status,
    }

    if source_file_id:
        clauses.append("_source_file_id = :source_file_id")
        params["source_file_id"] = _bind(source_file_id, dialect_name)
    if run_id:
        clauses.append("_run_id = :run_id")
        params["run_id"] = _bind(run_id, dialect_name)
    if batch_id:
        clauses.append("_batch_id = :batch_id")
        params["batch_id"] = _bind(batch_id, dialect_name)
    if unassigned_only:
        clauses.append("_batch_id IS NULL")
    if after_row_number > 0:
        clauses.append("_row_number > :after_row_number")
        params["after_row_number"] = after_row_number
    if limit is not None and limit > 0:
        params["limit"] = limit

    limit_sql = " LIMIT :limit" if limit is not None and limit > 0 else ""
    sql = text(
        f"SELECT * FROM {table_name} WHERE {' AND '.join(clauses)} "
        f"ORDER BY _row_number{limit_sql}"
    )
    with engine.connect() as conn:
        result = conn.execute(sql, params)
        return [dict(row._mapping) for row in result]


def tag_staging_rows(
    engine: Engine,
    table_name: str,
    *,
    row_ids: list[uuid.UUID],
    batch_id: uuid.UUID,
    run_id: uuid.UUID | None = None,
) -> int:
    if not row_ids:
        return 0
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return 0

    dialect_name = engine.dialect.name
    placeholders = ", ".join(f":id_{i}" for i in range(len(row_ids)))
    params: dict[str, Any] = {
        f"id_{i}": _bind(row_ids[i], dialect_name) for i in range(len(row_ids))
    }
    params["batch_id"] = _bind(batch_id, dialect_name)
    set_run = ""
    if run_id:
        set_run = ", _run_id = :run_id"
        params["run_id"] = _bind(run_id, dialect_name)

    sql = text(
        f"UPDATE {table_name} SET _batch_id = :batch_id{set_run} "
        f"WHERE _row_id IN ({placeholders})"
    )
    with engine.begin() as conn:
        result = conn.execute(sql, params)
        return int(result.rowcount or 0)


def count_staged_rows_for_batch(
    engine: Engine,
    table_name: str,
    *,
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    status: str = "staged",
) -> int:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return 0
    dialect_name = engine.dialect.name
    sql = text(
        f"SELECT COUNT(*) FROM {table_name} "
        f"WHERE _project_id = :project_id AND _batch_id = :batch_id AND _status = :status"
    )
    with engine.connect() as conn:
        return int(
            conn.execute(
                sql,
                {
                    "project_id": _bind(project_id, dialect_name),
                    "batch_id": _bind(batch_id, dialect_name),
                    "status": status,
                },
            ).scalar_one()
        )


def count_staged_rows(engine: Engine, table_name: str, project_id: uuid.UUID) -> int:
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return 0
    sql = text(f"SELECT COUNT(*) FROM {table_name} WHERE _project_id = :project_id")
    with engine.connect() as conn:
        return int(
            conn.execute(
                sql, {"project_id": _bind(project_id, engine.dialect.name)}
            ).scalar_one()
        )


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (datetime,)):
        return value
    return value
