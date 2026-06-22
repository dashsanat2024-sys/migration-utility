from collections.abc import Generator
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from migration_utility.config import get_settings
from migration_utility.datastore.base import Base
import migration_utility.datastore.models  # noqa: F401 — register ORM models

_engine = None
_SessionLocal = None


def _engine_kwargs(database_url: str) -> dict:
    """Serverless hosts (Vercel) should not hold connection pools between invocations."""
    kwargs: dict = {"pool_pre_ping": True}
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        kwargs["poolclass"] = NullPool
    if "neon.tech" in database_url and "sslmode=" not in database_url:
        sep = "&" if "?" in database_url else "?"
        kwargs["connect_args"] = {"sslmode": "require"}
    return kwargs


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())
