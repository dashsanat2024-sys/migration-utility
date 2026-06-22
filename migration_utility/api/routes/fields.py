from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from migration_utility.api.deps import get_db_session
from migration_utility.api.routes.rules import _get_project, _get_rule_set
from migration_utility.api.schemas import (
    ApplyFieldMappingsRequest,
    FieldCatalogFieldRead,
    FieldCatalogRead,
    FieldMappingSuggestionRead,
)
from migration_utility.fields.service import FieldCatalogService

router = APIRouter(prefix="/projects/{project_id}/fields", tags=["field-catalog"])


def _to_read(catalog) -> FieldCatalogRead:
    return FieldCatalogRead(
        id=catalog.id,
        project_id=catalog.project_id,
        entity=catalog.entity,
        source_fields=[FieldCatalogFieldRead(**f) for f in catalog.source_fields],
        target_fields=[FieldCatalogFieldRead(**f) for f in catalog.target_fields],
        source_filename=catalog.source_filename,
        target_filename=catalog.target_filename,
        created_at=catalog.created_at,
        updated_at=catalog.updated_at,
    )


@router.get("/{entity}", response_model=FieldCatalogRead | None)
def get_field_catalog(
    project_id: UUID,
    entity: str,
    db: Session = Depends(get_db_session),
):
    _get_project(project_id, db)
    catalog = FieldCatalogService(db).get(project_id, entity)
    if not catalog:
        return None
    return _to_read(catalog)


@router.post("/{entity}/source", response_model=FieldCatalogRead)
async def upload_source_fields(
    project_id: UUID,
    entity: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
):
    project = _get_project(project_id, db)
    text = (await file.read()).decode("utf-8-sig")
    try:
        catalog = FieldCatalogService(db).upload_source(
            project,
            entity,
            text=text,
            filename=file.filename or "source_fields.csv",
            content_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_read(catalog)


@router.post("/{entity}/target", response_model=FieldCatalogRead)
async def upload_target_fields(
    project_id: UUID,
    entity: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
):
    project = _get_project(project_id, db)
    text = (await file.read()).decode("utf-8-sig")
    try:
        catalog = FieldCatalogService(db).upload_target(
            project,
            entity,
            text=text,
            filename=file.filename or "target_fields.csv",
            content_type=file.content_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_read(catalog)


@router.post("/{entity}/suggest-mappings", response_model=list[FieldMappingSuggestionRead])
def suggest_mappings(
    project_id: UUID,
    entity: str,
    db: Session = Depends(get_db_session),
):
    _get_project(project_id, db)
    try:
        return FieldCatalogService(db).suggest_mappings(project_id, entity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/{entity}/apply-mappings/{rule_set_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def apply_catalog_mappings(
    project_id: UUID,
    entity: str,
    rule_set_id: UUID,
    body: ApplyFieldMappingsRequest,
    db: Session = Depends(get_db_session),
):
    _get_project(project_id, db)
    rule_set = _get_rule_set(project_id, rule_set_id, db)
    if rule_set.entity != entity:
        raise HTTPException(status_code=400, detail="Rule set entity does not match")
    try:
        FieldCatalogService(db).apply_mappings_to_rule_set(rule_set, body.mappings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return None
