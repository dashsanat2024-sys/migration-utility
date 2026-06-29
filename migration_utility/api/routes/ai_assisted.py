"""AI-assisted migration API — suggests only, never writes to Kraken."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from migration_utility.ai import (
    AiAssistantService,
    AiErrorTriageService,
    AiLookupService,
    AiMappingService,
    AiTransformRuleService,
    ai_status,
    is_ai_available,
)
from migration_utility.api.deps import get_db_session, get_plugin_registry
from migration_utility.api.routes.rules import _get_project
from migration_utility.api.schemas import (
    AiAssistantRequest,
    AiAssistantReplyRead,
    AiLookupSuggestionRead,
    AiStatusRead,
    AiSuggestLookupsRequest,
    AiSuggestTransformRulesRequest,
    AiTriageRequest,
    AiTriageReportRead,
    FieldMappingSuggestionRead,
)
from migration_utility.exceptions.service import ExceptionQueueService
from migration_utility.fields.service import FieldCatalogService
from migration_utility.plugins.registry import DestinationPluginRegistry

router = APIRouter(prefix="/projects/{project_id}/ai", tags=["ai-assisted"])


@router.get("/status", response_model=AiStatusRead)
def get_ai_status(project_id: UUID, db: Session = Depends(get_db_session)):
    _get_project(project_id, db)
    return AiStatusRead(**ai_status())


@router.post("/suggest-mappings/{entity}", response_model=list[FieldMappingSuggestionRead])
def ai_suggest_mappings(
    project_id: UUID,
    entity: str,
    destination_first: bool = Query(default=True),
    db: Session = Depends(get_db_session),
    plugin_registry: DestinationPluginRegistry = Depends(get_plugin_registry),
):
    if not is_ai_available():
        raise HTTPException(status_code=503, detail="AI-assisted layer is disabled or not configured")
    project = _get_project(project_id, db)
    svc = FieldCatalogService(db)
    catalog = svc.get(project_id, entity)
    if not catalog or not catalog.source_fields:
        raise HTTPException(status_code=400, detail="Upload source fields before AI suggest")

    target_fields = svc.resolve_destination_fields(project, entity, plugin_registry)
    if destination_first:
        rows = AiMappingService().suggest_schema_mappings(catalog.source_fields, target_fields)
    else:
        raise HTTPException(status_code=400, detail="AI suggest supports destination_first=true only")

    return [FieldMappingSuggestionRead(**row) for row in rows]


@router.post("/suggest-lookups/{entity}", response_model=AiLookupSuggestionRead)
def ai_suggest_lookups(
    project_id: UUID,
    entity: str,
    body: AiSuggestLookupsRequest | None = None,
    db: Session = Depends(get_db_session),
    plugin_registry: DestinationPluginRegistry = Depends(get_plugin_registry),
):
    if not is_ai_available():
        raise HTTPException(status_code=503, detail="AI-assisted layer is disabled")
    project = _get_project(project_id, db)
    svc = FieldCatalogService(db)
    catalog = svc.get(project_id, entity)
    if not catalog:
        raise HTTPException(status_code=400, detail="No field catalog for entity")

    req = body or AiSuggestLookupsRequest()
    mapping_rows = req.mappings
    if not mapping_rows:
        target_fields = svc.resolve_destination_fields(project, entity, plugin_registry)
        mapping_rows = AiMappingService().suggest_schema_mappings(catalog.source_fields, target_fields)

    column_samples = {
        f["name"]: f.get("sample_values") or []
        for f in catalog.source_fields
    }
    result = AiLookupService().suggest_lookups(mapping_rows, column_samples)
    return AiLookupSuggestionRead(**result.model_dump())


@router.post("/suggest-transform-rules/{entity}", response_model=list[FieldMappingSuggestionRead])
def ai_suggest_transform_rules(
    project_id: UUID,
    entity: str,
    body: AiSuggestTransformRulesRequest | None = None,
    db: Session = Depends(get_db_session),
    plugin_registry: DestinationPluginRegistry = Depends(get_plugin_registry),
):
    if not is_ai_available():
        raise HTTPException(status_code=503, detail="AI-assisted layer is disabled")
    project = _get_project(project_id, db)
    svc = FieldCatalogService(db)
    catalog = svc.get(project_id, entity)
    if not catalog:
        raise HTTPException(status_code=400, detail="No field catalog for entity")

    req = body or AiSuggestTransformRulesRequest()
    mapping_rows = req.mappings
    if not mapping_rows:
        target_fields = svc.resolve_destination_fields(project, entity, plugin_registry)
        mapping_rows = AiMappingService().suggest_schema_mappings(catalog.source_fields, target_fields)

    column_samples = {
        f["name"]: f.get("sample_values") or []
        for f in catalog.source_fields
    }
    rows = AiTransformRuleService().suggest_transform_rules(mapping_rows, column_samples)
    return [FieldMappingSuggestionRead(**row) for row in rows]


@router.post("/triage-errors", response_model=AiTriageReportRead)
def ai_triage_errors(
    project_id: UUID,
    body: AiTriageRequest,
    db: Session = Depends(get_db_session),
):
    if not is_ai_available():
        raise HTTPException(status_code=503, detail="AI-assisted layer is disabled")
    _get_project(project_id, db)

    errors: list[dict] = []
    if body.use_exception_queue:
        items = ExceptionQueueService(db).list_for_project(project_id, status=body.status)
        errors = [
            {
                "kraken_error_code": item.kraken_error_code,
                "error_reason": item.error_reason,
                "root_cause_category": item.root_cause_category,
                "owner_role": item.owner_role,
                "remediation_hint": item.remediation_hint,
                "payload": item.payload,
            }
            for item in items[: body.limit]
        ]
    else:
        errors = body.errors

    report = AiErrorTriageService().triage(errors)
    return AiTriageReportRead(**report.model_dump())


@router.post("/assistant", response_model=AiAssistantReplyRead)
def ai_assistant(
    project_id: UUID,
    body: AiAssistantRequest,
    db: Session = Depends(get_db_session),
):
    if not is_ai_available():
        raise HTTPException(status_code=503, detail="AI-assisted layer is disabled")
    _get_project(project_id, db)
    reply = AiAssistantService().answer(body.question, context=body.context)
    return AiAssistantReplyRead(**reply.model_dump())
