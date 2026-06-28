from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from migration_utility.api.deps import get_db_session, get_plugin_registry, get_schema_registry
from migration_utility.api.routes.destination import _plugin_to_read, _schema_to_read
from migration_utility.api.routes.fields import _to_read as catalog_to_read
from migration_utility.api.routes.project_lookup import resolve_project
from migration_utility.api.schemas import ProjectWorkspaceRead
from migration_utility.fields.service import FieldCatalogService
from migration_utility.plugins.registry import DestinationPluginRegistry
from migration_utility.rules.loader import RuleLoader
from migration_utility.schema.registry import SchemaRegistry

router = APIRouter(tags=["workspace"])


@router.get("/projects/{project_ref}/workspace", response_model=ProjectWorkspaceRead)
def get_project_workspace(
    project_ref: str,
    entity: str = Query(default="account"),
    db: Session = Depends(get_db_session),
    registry: DestinationPluginRegistry = Depends(get_plugin_registry),
    schema_registry: SchemaRegistry = Depends(get_schema_registry),
) -> ProjectWorkspaceRead:
    """Single round-trip payload for opening a project workspace (reduces serverless cold-start latency)."""
    project = resolve_project(project_ref, db)
    plugin = registry.resolve_for_project(project)
    schema = plugin.get_schema(entity)
    if not schema:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {plugin.id!r} has no schema for entity {entity!r}",
        )

    catalog = FieldCatalogService(db).get(project.id, entity)
    rule_sets = RuleLoader(db).list_for_project(project.id, entity)

    return ProjectWorkspaceRead(
        project=project,
        plugin=_plugin_to_read(plugin),
        destination_schema=_schema_to_read(schema),
        catalog=catalog_to_read(catalog) if catalog else None,
        rule_sets=rule_sets,
        entities=schema_registry.list_entities(),
    )
