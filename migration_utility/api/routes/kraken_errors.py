from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from migration_utility.kraken.errors.catalog import get_kraken_error_catalog

router = APIRouter(prefix="/kraken/error-codes", tags=["kraken-errors"])


@router.get("/summary")
def kraken_error_summary() -> dict:
    return get_kraken_error_catalog().summary()


@router.get("/categories")
def kraken_error_categories() -> list[dict]:
    return get_kraken_error_catalog().categories()


@router.get("")
def search_kraken_errors(
    q: str | None = None,
    category: str | None = None,
    phase: str | None = None,
    relevance: str | None = None,
    error_type: str | None = None,
    has_detail: bool | None = None,
    limit: int = Query(default=50, le=500),
) -> list[dict]:
    return get_kraken_error_catalog().search(
        q=q,
        category=category,
        phase=phase,
        relevance=relevance,
        error_type=error_type,
        has_detail=has_detail,
        limit=limit,
    )


@router.get("/pre-migration")
def pre_migration_kraken_errors() -> list[dict]:
    return get_kraken_error_catalog().pre_migration_codes()


@router.get("/{code}")
def get_kraken_error(code: str) -> dict:
    entry = get_kraken_error_catalog().get(code)
    if not entry:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Error code not found")
    return entry
