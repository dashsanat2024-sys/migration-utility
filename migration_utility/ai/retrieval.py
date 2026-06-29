"""Kraken error code retrieval for AI triage tools."""

from __future__ import annotations

from migration_utility.kraken.errors.catalog import get_kraken_error_catalog


def lookup_kraken_error(code: str) -> dict:
    catalog = get_kraken_error_catalog()
    entry = catalog.get(code)
    return entry or {"code": code, "message": "Unknown code", "has_detail": False}


def search_kraken_errors(query: str, *, limit: int = 5) -> list[dict]:
    catalog = get_kraken_error_catalog()
    return catalog.search(query, limit=limit)
