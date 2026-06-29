from __future__ import annotations

import logging
import time

from migration_utility.config import get_settings
from migration_utility.connectors.registry import build_default_registry
from migration_utility.core.enums import RunStatus
from migration_utility.datastore.models import Project
from migration_utility.datastore.session import get_session_factory
from migration_utility.schema.registry import build_default_schema_registry
from migration_utility.services.runner import RunService
from migration_utility.worker.claim import claim_next_queued_run, get_worker_id

logger = logging.getLogger(__name__)


def _registry():
    return build_default_registry(build_default_schema_registry())


def process_next_queued_run(db, *, worker_id: str | None = None) -> bool:
    """Claim and execute one queued migration run."""
    worker_id = worker_id or get_worker_id()
    run = claim_next_queued_run(db, worker_id=worker_id)
    if not run:
        return False

    project = db.get(Project, run.project_id)
    if not project:
        run.status = RunStatus.FAILED.value
        run.error_message = "Project not found"
        db.commit()
        return True

    service = RunService(db, _registry())
    service.execute_run(run, project)
    return True


def worker_loop() -> None:
    settings = get_settings()
    worker_id = get_worker_id()
    logger.info(
        "Migration worker %s started (poll=%ss, chunk=%s)",
        worker_id,
        settings.worker_poll_seconds,
        settings.run_chunk_size,
    )
    SessionLocal = get_session_factory()
    while True:
        db = SessionLocal()
        try:
            processed = process_next_queued_run(db, worker_id=worker_id)
        except Exception:
            logger.exception("Worker %s iteration failed", worker_id)
            processed = False
        finally:
            db.close()
        if not processed:
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=get_settings().log_level)
    worker_loop()
