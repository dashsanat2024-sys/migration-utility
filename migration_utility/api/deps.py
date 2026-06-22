from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from migration_utility.connectors.registry import ConnectorRegistry
from migration_utility.datastore.session import get_db
from migration_utility.ingest.preprocessors import PreProcessorRegistry
from migration_utility.schema.registry import SchemaRegistry
from migration_utility.schema.target_registry import TargetSchemaRegistry


def get_db_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_registry(request: Request) -> ConnectorRegistry:
    return request.app.state.registry


def get_schema_registry(request: Request) -> SchemaRegistry:
    return request.app.state.schema_registry


def get_preprocessors(request: Request) -> PreProcessorRegistry:
    return request.app.state.preprocessors


def get_target_registry(request: Request) -> TargetSchemaRegistry:
    return request.app.state.target_registry
