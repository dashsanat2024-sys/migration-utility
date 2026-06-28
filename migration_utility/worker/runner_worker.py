from __future__ import annotations

import logging
import time

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from migration_utility.config import get_settings
from migration_utility.connectors.registry import build_default_registry
from migration_utility.core.enums import RunStatus
from migration_utility.datastore.models import MigrationRun, Project
from migration_utility.datastore.session import get_session_factory
from migration_utility.schema.registry import build_default_schema_registry
from migration_utility.services.runner import RunService

logger = logging.getLogger(__name__)


def _registry():
    return build_default_registry(build_default_schema_registry())


def process_next_queued_run(db: Session) -> bool:
    """Claim and execute one queued migration run."""
    run = db.scalar(
        select(MigrationRun)
        .where(MigrationRun.status == RunStatus.QUEUED.value)
        .order_by(MigrationRun.created_at.asc())
        .limit(1)
    )
    if not run:
        return False

    project = db.get(Project, run.project_id)
    if not project:
        run.status = RunStatus.FAILED.value
        run.error_message = "Project not found"
        db.commit()
        return True

    run.status = RunStatus.RUNNING.value
    run.execution_mode = "async"
    run.progress_message = "Worker claimed run"
    db.commit()
    db.refresh(run)

    service = RunService(db, _registry())
    service.execute_run(run, project)
    return True


def worker_loop() -> None:
    settings = get_settings()
    logger.info(
        "Migration worker started (poll=%ss, chunk=%s)",
        settings.worker_poll_seconds,
        settings.run_chunk_size,
    )
    SessionLocal = get_session_factory()
    while True:
        db = SessionLocal()
        try:
            processed = process_next_queued_run(db)
        except Exception:
            logger.exception("Worker iteration failed")
            processed = False
        finally:
            db.close()
        if not processed:
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=get_settings().log_level)
    worker_loop()
