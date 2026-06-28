from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from migration_utility import __version__
from migration_utility.api.deps import get_db_session, get_registry
from migration_utility.api.schemas import HealthRead
from migration_utility.connectors.registry import ConnectorRegistry

router = APIRouter(tags=["health"])


@router.get("/health/live")
def health_live() -> dict[str, str]:
    """Lightweight liveness probe — no database (warms serverless without Neon latency)."""
    return {"status": "ok", "version": __version__}


@router.get("/health", response_model=HealthRead)
def health_check(
    db: Session = Depends(get_db_session),
    registry: ConnectorRegistry = Depends(get_registry),
) -> HealthRead:
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "degraded"

    return HealthRead(
        status=db_status,
        version=__version__,
        connectors={
            "sources": registry.list_sources(),
            "targets": registry.list_targets(),
        },
    )
