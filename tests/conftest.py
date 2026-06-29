"""Shared pytest configuration — force in-memory auth off unless a test opts in."""

from __future__ import annotations

import pytest

from migration_utility.config import get_settings


@pytest.fixture(autouse=True)
def _default_auth_disabled(monkeypatch):
    """Prevent .env AUTH_ENABLED=true from breaking SQLite test fixtures."""
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("AI_MOCK_MODE", "true")
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("AI_FORCE_HEURISTIC", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
