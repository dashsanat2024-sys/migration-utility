from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.api.deps import get_db_session
from migration_utility.api.schemas import ProjectCreate, ProjectRead, ProjectUpdate
from migration_utility.core.enums import AuditAction
from migration_utility.datastore.models import Project
from migration_utility.services.audit import write_audit

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(body: ProjectCreate, db: Session = Depends(get_db_session)) -> Project:
    existing = db.scalar(select(Project).where(Project.slug == body.slug))
    if existing:
        raise HTTPException(status_code=409, detail=f"Project slug {body.slug!r} already exists")

    project = Project(
        name=body.name,
        slug=body.slug,
        description=body.description,
        target_system=body.target_system,
        source_connector_key=body.source_connector_key,
        target_adapter_key=body.target_adapter_key,
        environment=body.environment,
        config=body.config,
    )
    db.add(project)
    db.flush()
    write_audit(
        db,
        entity_type="project",
        entity_id=str(project.id),
        action=AuditAction.CREATED,
        message=f"Project {project.slug} created",
        project_id=project.id,
    )
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(db: Session = Depends(get_db_session)) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())))


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: UUID, db: Session = Depends(get_db_session)) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID, body: ProjectUpdate, db: Session = Depends(get_db_session)
) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    if body.environment is not None:
        project.environment = body.environment
    if body.config is not None:
        project.config = body.config
    write_audit(
        db,
        entity_type="project",
        entity_id=str(project.id),
        action=AuditAction.UPDATED,
        message=f"Project {project.slug} updated",
        project_id=project.id,
    )
    db.commit()
    db.refresh(project)
    return project
