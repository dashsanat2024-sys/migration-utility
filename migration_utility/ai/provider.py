"""AI provider selection — LangChain when configured, heuristic fallback otherwise."""

from __future__ import annotations

from typing import Any, Literal

from migration_utility.config import get_settings

ProviderMode = Literal["langchain", "heuristic", "disabled"]


def is_ai_available() -> bool:
    settings = get_settings()
    if not settings.ai_enabled:
        return False
    return bool(settings.openai_api_key) or settings.ai_mock_mode


def provider_mode() -> ProviderMode:
    settings = get_settings()
    if not settings.ai_enabled:
        return "disabled"
    if settings.openai_api_key and not settings.ai_force_heuristic:
        return "langchain"
    if settings.ai_mock_mode:
        return "heuristic"
    return "disabled"


def ai_status() -> dict[str, Any]:
    mode = provider_mode()
    settings = get_settings()
    return {
        "enabled": settings.ai_enabled,
        "available": mode != "disabled",
        "provider": mode,
        "model": settings.ai_model if mode == "langchain" else None,
        "policy": "AI proposes; deterministic engine disposes. No AI in Kraken write path.",
    }


def get_chat_model() -> Any | None:
    """Return LangChain chat model or None (caller uses heuristic fallback)."""
    if provider_mode() != "langchain":
        return None
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        return None
    settings = get_settings()
    return ChatOpenAI(model=settings.ai_model, temperature=0, api_key=settings.openai_api_key)
