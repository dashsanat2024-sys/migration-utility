"""Atomic claim of queued migration runs for parallel workers."""

from __future__ import annotations

import os
import socket
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.config import get_settings
from migration_utility.core.enums import RunStatus
from migration_utility.datastore.models import MigrationRun


def get_worker_id() -> str:
    settings = get_settings()
    if settings.worker_id:
        return settings.worker_id
    return f"{socket.gethostname()}-{os.getpid()}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def claim_next_queued_run(db: Session, *, worker_id: str) -> MigrationRun | None:
    """Claim one queued run using row-level lock (SKIP LOCKED on PostgreSQL)."""
    dialect = db.bind.dialect.name if db.bind is not None else "postgresql"
    stmt = (
        select(MigrationRun)
        .where(MigrationRun.status == RunStatus.QUEUED.value)
        .order_by(MigrationRun.created_at.asc())
        .limit(1)
    )
    if dialect == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    else:
        stmt = stmt.with_for_update()

    run = db.scalar(stmt)
    if not run:
        return None

    now = _utcnow()
    run.status = RunStatus.RUNNING.value
    run.execution_mode = "async"
    run.claimed_by = worker_id
    run.claimed_at = now
    run.started_at = run.started_at or now
    run.progress_message = f"Claimed by {worker_id}"
    db.commit()
    db.refresh(run)
    return run
