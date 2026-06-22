from fastapi import APIRouter, Depends

from migration_utility.api.deps import get_schema_registry
from migration_utility.api.schemas import SchemaEntityRead, SchemaFieldRead
from migration_utility.schema.registry import SchemaRegistry

router = APIRouter(prefix="/schema", tags=["schema"])


@router.get("/entities", response_model=list[str])
def list_entities(registry: SchemaRegistry = Depends(get_schema_registry)) -> list[str]:
    return registry.list_entities()


@router.get("/entities/{name}", response_model=SchemaEntityRead)
def get_entity(name: str, registry: SchemaRegistry = Depends(get_schema_registry)) -> SchemaEntityRead:
    entity = registry.get(name)
    if entity is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail=f"Entity {name!r} not found")
    return SchemaEntityRead(
        name=entity.name,
        description=entity.description,
        fields=[
            SchemaFieldRead(
                name=f.name,
                data_type=f.data_type,
                required=f.required,
                description=f.description,
            )
            for f in entity.fields
        ],
    )
