from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.datastore.models import Project


def resolve_project(project_ref: str, db: Session) -> Project:
    """Load a project by UUID or human-readable slug (browser URL uses slug)."""
    ref = project_ref.strip()
    project: Project | None = None
    try:
        project = db.get(Project, UUID(ref))
    except ValueError:
        pass
    if project is None:
        project = db.scalar(select(Project).where(Project.slug == ref))
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
