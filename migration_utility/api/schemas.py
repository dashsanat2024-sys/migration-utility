from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=128, pattern=r"^[a-z0-9-]+$")
    description: str | None = None
    target_system: str = "generic"
    source_connector_key: str = "mock"
    target_adapter_key: str = "mock"
    environment: str = "dev"
    config: dict[str, Any] = Field(default_factory=dict)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    environment: str | None = None
    target_adapter_key: str | None = None
    config: dict[str, Any] | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    description: str | None
    target_system: str
    source_connector_key: str
    target_adapter_key: str
    environment: str
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class BatchCreate(BaseModel):
    batch_number: int = Field(..., ge=1)
    batch_config: dict[str, Any] = Field(default_factory=dict)


class MigrationRunCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    run_config: dict[str, Any] = Field(default_factory=dict)
    batches: list[BatchCreate] = Field(default_factory=lambda: [BatchCreate(batch_number=1)])


class BatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    batch_number: int
    status: str
    batch_config: dict[str, Any]
    stats: dict[str, Any] | None


class MigrationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    status: str
    run_config: dict[str, Any]
    result_summary: dict[str, Any] | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    progress_pct: int = 0
    progress_message: str | None = None
    checkpoint: dict[str, Any] = Field(default_factory=dict)
    execution_mode: str = "sync"
    batches: list[BatchRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    entity_id: str
    action: str
    message: str | None
    details: dict[str, Any] | None
    actor: str | None
    created_at: datetime


class HealthRead(BaseModel):
    status: str
    version: str
    connectors: dict[str, list[str]]


class SchemaFieldRead(BaseModel):
    name: str
    data_type: str
    required: bool
    description: str = ""
    constraints: dict[str, Any] = Field(default_factory=dict)


class SchemaEntityRead(BaseModel):
    name: str
    description: str
    fields: list[SchemaFieldRead]


class IngestFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    entity: str
    original_filename: str
    landing_path: str
    file_format: str
    status: str
    total_rows: int
    staged_count: int
    error_count: int
    staging_table: str | None
    message: str | None
    created_at: datetime
    updated_at: datetime


class IngestErrorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    ingest_file_id: UUID
    entity: str
    row_number: int
    raw_payload: dict[str, Any]
    error_reason: str
    resolved: bool
    created_at: datetime
    updated_at: datetime


class StagingStatsRead(BaseModel):
    entity: str
    staging_table: str
    row_count: int


class ValidationRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    rule_type: str
    field_name: str | None
    config: dict[str, Any]
    sort_order: int
    enabled: bool


class FieldMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_field: str | None
    target_field: str
    transform_type: str
    config: dict[str, Any]
    sort_order: int
    enabled: bool
    ai_suggested: bool = False
    ai_reasoning: str | None = None
    ai_confidence: float | None = None


class RuleSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    entity: str
    name: str
    description: str | None
    version: int
    workflow_state: str
    validation_rules: list[ValidationRuleRead] = Field(default_factory=list)
    field_mappings: list[FieldMappingRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class RuleSetCreate(BaseModel):
    entity: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class ValidationRuleCreate(BaseModel):
    name: str
    rule_type: str
    field_name: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0


class FieldMappingCreate(BaseModel):
    source_field: str | None = None
    target_field: str
    transform_type: str = "copy"
    config: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0


class TransformPreviewRequest(BaseModel):
    records: list[dict[str, Any]] = Field(default_factory=list)
    mappings: list[FieldMappingCreate] | None = None


class TransformPreviewRead(BaseModel):
    records: list[dict[str, Any]] = Field(default_factory=list)


class WorkflowTransition(BaseModel):
    workflow_state: str
    actor: str = Field(default="anonymous", max_length=128)
    role: str = Field(default="mapping_lead")
    comment: str | None = None


class MappingMatrixRow(BaseModel):
    source_field: str | None = None
    source_type: str | None = None
    source_required: bool = False
    target_field: str | None = None
    transform_type: str = "copy"
    config: dict[str, Any] = Field(default_factory=dict)
    mapping_id: str | None = None
    enabled: bool = True
    status: str = "unmapped"


class MappingMatrixRead(BaseModel):
    entity: str
    rule_set_id: str
    workflow_state: str
    editable: bool
    source_fields: list[dict[str, Any]]
    target_fields: list[dict[str, Any]]
    rows: list[MappingMatrixRow]
    coverage: dict[str, Any]
    field_catalog: dict[str, Any] | None = None


class FieldCatalogFieldRead(BaseModel):
    name: str
    data_type: str = "string"
    required: bool = False
    description: str = ""


class FieldCatalogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    entity: str
    source_fields: list[FieldCatalogFieldRead]
    target_fields: list[FieldCatalogFieldRead]
    source_filename: str | None
    target_filename: str | None
    created_at: datetime
    updated_at: datetime


class FieldMappingSuggestionRead(BaseModel):
    source_field: str | None = None
    source_type: str | None = None
    source_required: bool = False
    target_field: str | None = None
    target_type: str | None = None
    target_required: bool = False
    target_description: str = ""
    target_constraints: dict[str, Any] = Field(default_factory=dict)
    transform_type: str = "copy"
    config: dict[str, Any] = Field(default_factory=dict)
    status: str = "unmapped"
    match_confidence: str = "none"
    confidence_score: float | None = None
    ai_suggested: bool = False
    ai_reasoning: str = ""
    sample_values: list[str] = Field(default_factory=list)
    uncovered_source_values: list[str] = Field(default_factory=list)


class DestinationPluginRead(BaseModel):
    id: str
    label: str
    version: str
    adapter_key: str
    transport: str = "REST API"


class DestinationSchemaRead(BaseModel):
    entity: str
    description: str = ""
    fields: list[SchemaFieldRead] = Field(default_factory=list)


class ProjectWorkspaceRead(BaseModel):
    project: ProjectRead
    plugin: DestinationPluginRead
    destination_schema: DestinationSchemaRead
    catalog: FieldCatalogRead | None = None
    rule_sets: list[RuleSetRead] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=lambda: ["account"])


class SwapDestinationPluginRequest(BaseModel):
    plugin_id: str = Field(..., min_length=1)
    confirm_orphan: bool = False


class ApplyFieldMappingsRequest(BaseModel):
    mappings: list[dict[str, Any]]


class MappingMatrixUpdate(BaseModel):
    rows: list[dict[str, Any]]


class MappingApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    entity_id: UUID
    from_state: str
    to_state: str
    actor: str
    role: str
    comment: str | None
    created_at: datetime


class TariffMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_code: str
    target_code: str
    description: str | None
    config: dict[str, Any]
    sort_order: int
    enabled: bool


class TariffMappingSetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    description: str | None
    version: int
    workflow_state: str
    loaded_at: datetime | None
    mappings: list[TariffMappingRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TariffMappingSetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class TariffMappingCreate(BaseModel):
    source_code: str
    target_code: str
    description: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    sort_order: int = 0


class TariffLoadResult(BaseModel):
    loaded: int
    failed: int
    records: list[dict[str, Any]] = Field(default_factory=list)


class SelectionCriterionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    field_name: str
    operator: str
    value: Any | None
    enabled: bool
    sort_order: int
    label: str | None


class SelectionProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    entity: str
    name: str
    description: str | None
    logic: str
    max_candidates: int | None
    is_default: bool
    enabled: bool
    criteria: list[SelectionCriterionRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SelectionProfileCreate(BaseModel):
    entity: str = Field(..., min_length=1, max_length=128)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    logic: str = "and"
    max_candidates: int | None = Field(default=None, ge=1)
    is_default: bool = False


class SelectionCriterionCreate(BaseModel):
    field_name: str
    operator: str
    value: Any | None = None
    label: str | None = None
    sort_order: int = 0
    enabled: bool = True


class CriterionToggle(BaseModel):
    enabled: bool


class SelectionPreviewRequest(BaseModel):
    entity: str = "account"
    profile_id: UUID | None = None
    limit: int | None = Field(default=None, ge=1)


class SelectionPreviewRead(BaseModel):
    profile_id: str
    profile_name: str
    total_available: int
    selected_count: int
    excluded_count: int
    sample: list[dict[str, Any]] = Field(default_factory=list)


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    batch_id: UUID
    external_id: str
    status: str
    payload: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class LoadRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    run_id: UUID | None
    batch_id: UUID | None
    target_adapter_key: str
    entity: str
    external_id: str
    status: str
    request_payload: dict[str, Any] | None
    response_payload: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class LoadSummaryRead(BaseModel):
    loaded: int
    failed: int
    total: int


class ReconciliationCountsRead(BaseModel):
    staged_total: int
    ingest_errors_open: int
    runs_total: int
    runs_completed: int
    runs_failed: int
    loads_ok: int
    loads_failed: int


class ReconciliationRunSummaryItem(BaseModel):
    run_id: str
    name: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None


class ReconciliationSummaryRead(BaseModel):
    project_id: str
    entity: str
    staging_table: str
    counts: ReconciliationCountsRead
    recent_runs: list[ReconciliationRunSummaryItem] = Field(default_factory=list)


class ReconciliationFunnelRead(BaseModel):
    staged_in_run: int
    candidates_selected: int
    candidates_loaded: int
    candidates_failed: int
    target_loaded: int
    target_failed: int


class ReconciliationVarianceRead(BaseModel):
    staged_minus_selected: int
    selected_minus_target_ok: int
    unaccounted: int


class ReconciliationSampleRead(BaseModel):
    external_id: str
    candidate_status: str
    load_status: str | None
    source_payload: dict[str, Any]
    target_payload: dict[str, Any]
    diff_fields: list[str]
    reconciled: bool


class ReconciliationRunRead(BaseModel):
    run_id: str
    run_name: str
    run_status: str
    entity: str
    funnel: ReconciliationFunnelRead
    variance: ReconciliationVarianceRead
    match_rate: float | None
    reconciliation_status: str
    candidate_status: dict[str, int]
    load_status: dict[str, int]
    ingest_errors_open: int
    batch_stage_stats: list[dict[str, Any]] = Field(default_factory=list)
    samples: list[ReconciliationSampleRead] = Field(default_factory=list)


class ReconciliationExportRead(BaseModel):
    project_id: str
    project_slug: str
    entity: str
    generated_at: str
    summary: ReconciliationCountsRead
    runs: list[dict[str, Any]]
    load_records: list[dict[str, Any]]


class StwTransformRulesRead(BaseModel):
    property_type: dict[str, Any]
    area_code: dict[str, Any]
    rateband: dict[str, Any]
    overrides: dict[str, Any] = Field(default_factory=dict)
    tariff_table: list[dict[str, Any]] = Field(default_factory=list)


class StwTransformRulePatch(BaseModel):
    rules: dict[str, Any] = Field(default_factory=dict)


class StwTariffTableUpdate(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)


class StwTransformPreviewRequest(BaseModel):
    rule_key: str = Field(..., pattern=r"^(property_type|area_code|rateband)$")
    record: dict[str, Any] = Field(default_factory=dict)


class StwTransformPreviewRead(BaseModel):
    rule_key: str
    result: Any
    record: dict[str, Any]


class AiStatusRead(BaseModel):
    enabled: bool
    available: bool
    provider: str
    model: str | None = None
    policy: str = ""


class AiLookupSuggestionRead(BaseModel):
    gaps: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""


class AiTriageRequest(BaseModel):
    use_exception_queue: bool = True
    status: str | None = "open"
    limit: int = Field(default=200, ge=1, le=1000)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class AiTriageReportRead(BaseModel):
    total_errors: int = 0
    clusters: list[dict[str, Any]] = Field(default_factory=list)
    executive_summary: str = ""
    provider: str = "heuristic"


class AiSuggestLookupsRequest(BaseModel):
    mappings: list[dict[str, Any]] = Field(default_factory=list)


class AiSuggestTransformRulesRequest(BaseModel):
    mappings: list[dict[str, Any]] = Field(default_factory=list)


class AiAssistantRequest(BaseModel):
    question: str = Field(..., min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class AiAssistantReplyRead(BaseModel):
    answer: str
    references: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
