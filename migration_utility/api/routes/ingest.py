import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.api.deps import get_db_session, get_preprocessors, get_schema_registry
from migration_utility.api.schemas import IngestErrorRead, IngestFileRead, StagingStatsRead
from migration_utility.datastore.models import IngestError, IngestFile, Project
from migration_utility.datastore.session import get_engine
from migration_utility.ingest.preprocessors import PreProcessorRegistry
from migration_utility.ingest.service import IngestService
from migration_utility.ingest.staging import count_staged_rows, staging_table_name
from migration_utility.schema.registry import SchemaRegistry

router = APIRouter(prefix="/projects/{project_id}/ingest", tags=["ingest"])


def _get_project(project_id: UUID, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _ingest_service(
    db: Session,
    schema_registry: SchemaRegistry,
    preprocessors: PreProcessorRegistry,
) -> IngestService:
    return IngestService(db, schema_registry, preprocessors, engine=get_engine())


@router.post("/upload", response_model=IngestFileRead, status_code=status.HTTP_201_CREATED)
async def upload_and_ingest(
    project_id: UUID,
    entity: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
    schema_registry: SchemaRegistry = Depends(get_schema_registry),
    preprocessors: PreProcessorRegistry = Depends(get_preprocessors),
) -> IngestFile:
    project = _get_project(project_id, db)
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    service = _ingest_service(db, schema_registry, preprocessors)
    try:
        ingest_file = service.register_upload(
            project,
            entity=entity,
            original_filename=file.filename,
            temp_path=tmp_path,
            content_type=file.content_type,
        )
        ingest_file = service.process_file(ingest_file, project)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return ingest_file


@router.get("/files", response_model=list[IngestFileRead])
def list_ingest_files(project_id: UUID, db: Session = Depends(get_db_session)) -> list[IngestFile]:
    _get_project(project_id, db)
    stmt = (
        select(IngestFile)
        .where(IngestFile.project_id == project_id)
        .order_by(IngestFile.created_at.desc())
    )
    return list(db.scalars(stmt))


@router.get("/files/{file_id}", response_model=IngestFileRead)
def get_ingest_file(
    project_id: UUID, file_id: UUID, db: Session = Depends(get_db_session)
) -> IngestFile:
    _get_project(project_id, db)
    ingest_file = db.get(IngestFile, file_id)
    if not ingest_file or ingest_file.project_id != project_id:
        raise HTTPException(status_code=404, detail="Ingest file not found")
    return ingest_file


@router.post("/files/{file_id}/process", response_model=IngestFileRead)
def reprocess_file(
    project_id: UUID,
    file_id: UUID,
    db: Session = Depends(get_db_session),
    schema_registry: SchemaRegistry = Depends(get_schema_registry),
    preprocessors: PreProcessorRegistry = Depends(get_preprocessors),
) -> IngestFile:
    project = _get_project(project_id, db)
    ingest_file = db.get(IngestFile, file_id)
    if not ingest_file or ingest_file.project_id != project_id:
        raise HTTPException(status_code=404, detail="Ingest file not found")

    service = _ingest_service(db, schema_registry, preprocessors)
    return service.process_file(ingest_file, project)


@router.get("/errors", response_model=list[IngestErrorRead])
def list_ingest_errors(
    project_id: UUID,
    resolved: bool | None = None,
    db: Session = Depends(get_db_session),
) -> list[IngestError]:
    _get_project(project_id, db)
    stmt = select(IngestError).where(IngestError.project_id == project_id)
    if resolved is not None:
        stmt = stmt.where(IngestError.resolved == resolved)
    stmt = stmt.order_by(IngestError.created_at.desc())
    return list(db.scalars(stmt))


@router.post("/errors/{error_id}/reprocess", response_model=IngestErrorRead)
def reprocess_error_row(
    project_id: UUID,
    error_id: UUID,
    db: Session = Depends(get_db_session),
    schema_registry: SchemaRegistry = Depends(get_schema_registry),
    preprocessors: PreProcessorRegistry = Depends(get_preprocessors),
) -> IngestError:
    project = _get_project(project_id, db)
    error = db.get(IngestError, error_id)
    if not error or error.project_id != project_id:
        raise HTTPException(status_code=404, detail="Ingest error not found")

    service = _ingest_service(db, schema_registry, preprocessors)
    return service.reprocess_error(error, project)


@router.get("/staging/{entity}/stats", response_model=StagingStatsRead)
def staging_stats(
    project_id: UUID, entity: str, db: Session = Depends(get_db_session)
) -> StagingStatsRead:
    project = _get_project(project_id, db)
    table_name = staging_table_name(project.slug, entity)
    count = count_staged_rows(get_engine(), table_name, project.id)
    return StagingStatsRead(entity=entity, staging_table=table_name, row_count=count)
