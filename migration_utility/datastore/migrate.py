"""Apply Alembic migrations (used on Vercel cold start where Mangum lifespan is off)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_migrated = False


def run_migrations() -> None:
    global _migrated
    if _migrated:
        return
    try:
        from alembic import command
        from alembic.config import Config

        from migration_utility.config import get_settings

        settings = get_settings()
        if not settings.database_url or not settings.database_url.startswith("postgresql"):
            logger.warning("Skipping migrations — DATABASE_URL not configured")
            return

        cfg = Config("alembic.ini")
        cfg.set_main_option("sqlalchemy.url", settings.database_url)
        command.upgrade(cfg, "head")
        _migrated = True
        logger.info("Database migrations applied (alembic upgrade head)")
    except Exception as exc:
        logger.warning("Database migration skipped or failed: %s", exc)
