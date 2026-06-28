from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.api.deps import get_db_session
from migration_utility.datastore.models import DataProfile, IngestFile, Project

router = APIRouter(tags=["profiling"])


class DataProfileRead(BaseModel):
    id: UUID
    project_id: UUID
    ingest_file_id: UUID | None
    entity: str
    row_count: int
    column_stats: list
    anomalies: list
    summary: dict

    model_config = {"from_attributes": True}


@router.get("/projects/{project_id}/ingest/files/{file_id}/profile", response_model=DataProfileRead)
def get_ingest_file_profile(
    project_id: UUID,
    file_id: UUID,
    db: Session = Depends(get_db_session),
) -> DataProfile:
    _get_project(project_id, db)
    ingest_file = db.get(IngestFile, file_id)
    if not ingest_file or ingest_file.project_id != project_id:
        raise HTTPException(status_code=404, detail="Ingest file not found")
    profile = db.scalar(
        select(DataProfile)
        .where(DataProfile.ingest_file_id == file_id)
        .order_by(DataProfile.created_at.desc())
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not generated yet — re-upload or process file")
    return profile


@router.get("/projects/{project_id}/profiles", response_model=list[DataProfileRead])
def list_project_profiles(
    project_id: UUID,
    db: Session = Depends(get_db_session),
) -> list[DataProfile]:
    _get_project(project_id, db)
    return list(
        db.scalars(
            select(DataProfile)
            .where(DataProfile.project_id == project_id)
            .order_by(DataProfile.created_at.desc())
        )
    )


def _get_project(project_id: UUID, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
