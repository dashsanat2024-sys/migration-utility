import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from migration_utility import __version__
from migration_utility.api.routes import candidates, destination, fields, health, ingest, mapping, migration_runs, projects, reconciliation, rules, schema, selection, tariffs
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

    return app


app = create_app()
