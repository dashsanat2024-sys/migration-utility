from enum import StrEnum


class PipelineStage(StrEnum):
    INGEST = "ingest"
    VALIDATE = "validate"
    TRANSFORM = "transform"
    LOAD = "load"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CandidateStatus(StrEnum):
    SELECTED = "selected"
    STAGED = "staged"
    VALIDATED = "validated"
    TRANSFORMED = "transformed"
    LOADED = "loaded"
    FAILED = "failed"
    EXCLUDED = "excluded"


class AuditAction(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    PIPELINE_STAGE = "pipeline_stage"
    ERROR = "error"


class IngestFileStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
