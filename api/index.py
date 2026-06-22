"""Vercel serverless entrypoint for the FastAPI application."""

from mangum import Mangum

from migration_utility.main import app

handler = Mangum(app, lifespan="off")
