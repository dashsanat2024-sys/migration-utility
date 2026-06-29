import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from migration_utility import __version__
from migration_utility.api.routes import account_health, ai_assisted, auth, candidates, destination, exceptions, fields, health, ingest, kraken_errors, mapping, migration_runs, profiling, projects, reconciliation, rules, schema, selection, stw_transform_rules, tariffs, workspace
from migration_utility.auth.service import ensure_seed_admin
from migration_utility.config import get_settings
from migration_utility.connectors.registry import build_default_registry
from migration_utility.ingest.preprocessors import build_default_preprocessors
from migration_utility.plugins.registry import build_default_plugin_registry
from migration_utility.schema.registry import build_default_schema_registry
from migration_utility.schema.target_registry import build_default_target_registry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    logger.info("Migration Utility v%s starting", __version__)
    logger.info(
        "Connectors — sources: %s, targets: %s",
        app.state.registry.list_sources(),
        app.state.registry.list_targets(),
    )
    logger.info("Landing zone: %s", settings.landing_zone_path)
    from migration_utility.datastore.migrate import run_migrations

    run_migrations()
    if settings.auth_enabled:
        from sqlalchemy.exc import OperationalError, ProgrammingError

        from migration_utility.datastore.session import get_session_factory

        db = get_session_factory()()
        try:
            ensure_seed_admin(db)
            logger.info("Auth enabled — seed admin ensured")
        except (ProgrammingError, OperationalError) as exc:
            db.rollback()
            logger.warning("Auth seed skipped — run alembic upgrade head: %s", exc)
        finally:
            db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    schema_registry = build_default_schema_registry()
    target_registry = build_default_target_registry()
    plugin_registry = build_default_plugin_registry()

    app = FastAPI(
        title="Migration Utility",
        description="Generic data migration engine",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.schema_registry = schema_registry
    app.state.target_registry = target_registry
    app.state.plugin_registry = plugin_registry
    app.state.registry = build_default_registry(schema_registry)
    app.state.preprocessors = build_default_preprocessors()

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(projects.router, prefix="/api")
    app.include_router(migration_runs.router, prefix="/api")
    app.include_router(schema.router, prefix="/api")
    app.include_router(destination.router, prefix="/api")
    app.include_router(ingest.router, prefix="/api")
    app.include_router(rules.router, prefix="/api")
    app.include_router(selection.router, prefix="/api")
    app.include_router(candidates.router, prefix="/api")
    app.include_router(mapping.router, prefix="/api")
    app.include_router(fields.router, prefix="/api")
    app.include_router(tariffs.router, prefix="/api")
    app.include_router(reconciliation.router, prefix="/api")
    app.include_router(exceptions.router, prefix="/api")
    app.include_router(profiling.router, prefix="/api")
    app.include_router(kraken_errors.router, prefix="/api")
    app.include_router(account_health.router, prefix="/api")
    app.include_router(stw_transform_rules.router, prefix="/api")
    app.include_router(ai_assisted.router, prefix="/api")
    app.include_router(workspace.router, prefix="/api")

    return app


app = create_app()
