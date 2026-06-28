from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from migration_utility.config import get_settings


def build_http_client(**overrides: Any) -> httpx.Client:
    """HTTP client with corporate proxy and optional mTLS for on-prem runners."""
    settings = get_settings()
    kwargs: dict[str, Any] = {
        "timeout": httpx.Timeout(settings.http_timeout_seconds),
        "follow_redirects": True,
    }
    proxy = settings.http_proxy or settings.https_proxy
    if proxy:
        kwargs["proxy"] = proxy
    cert = settings.client_cert_path
    if cert and settings.client_key_path:
        kwargs["cert"] = (cert, settings.client_key_path)
    elif cert:
        kwargs["cert"] = cert
    if settings.ca_bundle_path:
        kwargs["verify"] = settings.ca_bundle_path
    kwargs.update(overrides)
    return httpx.Client(**kwargs)


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> httpx.Response:
    with build_http_client() as client:
        return client.post(url, json=payload, headers=headers or {})
