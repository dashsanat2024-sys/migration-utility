"""Vercel serverless entrypoint for the FastAPI application."""

import logging

from mangum import Mangum

from migration_utility.datastore.migrate import run_migrations

logging.basicConfig(level=logging.INFO)
run_migrations()

from migration_utility.main import app

handler = Mangum(app, lifespan="off")
