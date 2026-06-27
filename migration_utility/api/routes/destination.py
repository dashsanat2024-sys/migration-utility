from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from migration_utility.api.deps import get_db_session, get_plugin_registry
from migration_utility.api.routes.rules import _get_project
from migration_utility.api.schemas import (
    DestinationPluginRead,
    DestinationSchemaRead,
    SchemaFieldRead,
    SwapDestinationPluginRequest,
)
from migration_utility.datastore.models import Project
from migration_utility.fields.service import FieldCatalogService
from migration_utility.plugins.registry import DestinationPluginRegistry, resolve_plugin_id

router = APIRouter(tags=["destination"])


def _plugin_to_read(plugin) -> DestinationPluginRead:
    return DestinationPluginRead(
        id=plugin.id,
        label=plugin.label,
        version=plugin.version,
        adapter_key=plugin.adapter_key,
        transport=plugin.transport,
    )


def _schema_to_read(schema) -> DestinationSchemaRead:
    return DestinationSchemaRead(
        entity=schema.entity,
        description=schema.description,
        fields=[
            SchemaFieldRead(
                name=f.name,
                data_type=f.data_type,
                required=f.required,
                description=f.description,
                constraints=f.constraints,
            )
            for f in schema.fields
        ],
    )


@router.get("/destination/plugins", response_model=list[DestinationPluginRead])
def list_destination_plugins(
    registry: DestinationPluginRegistry = Depends(get_plugin_registry),
) -> list[DestinationPluginRead]:
    return [_plugin_to_read(p) for p in registry.list_plugins()]


@router.get("/projects/{project_id}/destination/schema", response_model=DestinationSchemaRead)
def get_project_destination_schema(
    project_id: UUID,
    entity: str = Query(default="account"),
    db: Session = Depends(get_db_session),
    registry: DestinationPluginRegistry = Depends(get_plugin_registry),
) -> DestinationSchemaRead:
    project = _get_project(project_id, db)
    plugin = registry.resolve_for_project(project)
    schema = plugin.get_schema(entity)
    if not schema:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {plugin.id!r} has no schema for entity {entity!r}",
        )
    return _schema_to_read(schema)


@router.get("/projects/{project_id}/destination/plugin", response_model=DestinationPluginRead)
def get_project_destination_plugin(
    project_id: UUID,
    db: Session = Depends(get_db_session),
    registry: DestinationPluginRegistry = Depends(get_plugin_registry),
) -> DestinationPluginRead:
    project = _get_project(project_id, db)
    plugin = registry.resolve_for_project(project)
    return _plugin_to_read(plugin)


@router.post("/projects/{project_id}/destination/swap", response_model=DestinationPluginRead)
def swap_destination_plugin(
    project_id: UUID,
    body: SwapDestinationPluginRequest,
    db: Session = Depends(get_db_session),
    registry: DestinationPluginRegistry = Depends(get_plugin_registry),
) -> DestinationPluginRead:
    project = _get_project(project_id, db)
    plugin = registry.get(body.plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin {body.plugin_id!r} not found")

    current_id = resolve_plugin_id(project)
    if current_id == body.plugin_id:
        return _plugin_to_read(plugin)

    catalog_svc = FieldCatalogService(db)
    has_mappings = False
    for catalog in [catalog_svc.get(project.id, "account")]:
        if catalog and catalog.target_fields:
            has_mappings = True
            break

    if has_mappings and not body.confirm_orphan:
        raise HTTPException(
            status_code=409,
            detail="Switching plugins may orphan existing mappings. Set confirm_orphan=true to proceed.",
        )

    config = dict(project.config or {})
    config["destination_plugin_id"] = body.plugin_id
    project.config = config
    project.target_adapter_key = plugin.adapter_key
    project.target_system = plugin.adapter_key
    db.commit()
    db.refresh(project)
    return _plugin_to_read(plugin)
