from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from migration_utility.core.enums import AuditAction
from migration_utility.datastore.models import AuditLog


def write_audit(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    action: AuditAction,
    message: str = "",
    details: dict[str, Any] | None = None,
    project_id: UUID | None = None,
    run_id: UUID | None = None,
    actor: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        project_id=project_id,
        run_id=run_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action.value,
        message=message,
        details=details,
        actor=actor,
    )
    db.add(entry)
    return entry
