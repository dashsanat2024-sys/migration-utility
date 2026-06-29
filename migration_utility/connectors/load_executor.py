"""Batched destination load with concurrency, rate limiting, and retry."""

from __future__ import annotations

import logging
import re
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

from migration_utility.config import Settings, get_settings

logger = logging.getLogger(__name__)

_BATCH_HANDLER = Callable[[list[dict[str, Any]]], tuple[list[dict[str, Any]], list[dict[str, Any]]]]
_KRAKEN_RATE_LIMIT_RE = re.compile(r"KT-(?:CT|GB)-1199\b", re.I)


class RateLimitError(Exception):
    """Raised when the destination signals a retryable rate limit."""

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


@dataclass(frozen=True)
class LoadBatchConfig:
    batch_size: int = 200
    concurrency: int = 4
    max_rps: float = 0.0
    retry_max: int = 5
    retry_base_seconds: float = 1.0

    @classmethod
    def from_settings(
        cls,
        settings: Settings | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> LoadBatchConfig:
        settings = settings or get_settings()
        base = cls(
            batch_size=settings.load_batch_size,
            concurrency=settings.load_concurrency,
            max_rps=settings.load_max_rps,
            retry_max=settings.load_retry_max,
            retry_base_seconds=settings.load_retry_base_seconds,
        )
        if not overrides:
            return base
        return cls(
            batch_size=int(overrides.get("load_batch_size", base.batch_size)),
            concurrency=max(1, int(overrides.get("load_concurrency", base.concurrency))),
            max_rps=float(overrides.get("load_max_rps", base.max_rps)),
            retry_max=max(0, int(overrides.get("load_retry_max", base.retry_max))),
            retry_base_seconds=float(
                overrides.get("load_retry_base_seconds", base.retry_base_seconds)
            ),
        )


def chunk_records(records: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    if batch_size <= 0 or len(records) <= batch_size:
        return [records] if records else []
    return [records[i : i + batch_size] for i in range(0, len(records), batch_size)]


def is_rate_limited_http(status_code: int, body: str) -> bool:
    if status_code == 429:
        return True
    if _KRAKEN_RATE_LIMIT_RE.search(body):
        return True
    lowered = body.lower()
    return status_code == 503 and "rate" in lowered


def parse_retry_after_seconds(response_headers: dict[str, str] | None) -> float | None:
    if not response_headers:
        return None
    raw = response_headers.get("Retry-After") or response_headers.get("retry-after")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        return None


class _RateLimiter:
    def __init__(self, max_rps: float) -> None:
        self._interval = 1.0 / max_rps if max_rps > 0 else 0.0
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        if self._interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            if now < self._next_allowed:
                time.sleep(self._next_allowed - now)
                now = time.monotonic()
            self._next_allowed = now + self._interval


def run_batched_load(
    records: list[dict[str, Any]],
    handler: _BATCH_HANDLER,
    *,
    config: LoadBatchConfig | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split records into batches, load with concurrency, retry rate limits."""
    if not records:
        return [], []

    config = config or LoadBatchConfig.from_settings()
    batches = chunk_records(records, config.batch_size)
    if len(batches) == 1 and config.concurrency <= 1:
        return _run_batch_with_retry(batches[0], handler, config)

    limiter = _RateLimiter(config.max_rps)
    loaded: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    workers = min(config.concurrency, len(batches))

    def _submit_batch(batch: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        limiter.wait()
        return _run_batch_with_retry(batch, handler, config)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_submit_batch, batch): batch for batch in batches}
        for future in as_completed(futures):
            batch_loaded, batch_failed = future.result()
            loaded.extend(batch_loaded)
            failed.extend(batch_failed)

    return loaded, failed


def _run_batch_with_retry(
    batch: list[dict[str, Any]],
    handler: _BATCH_HANDLER,
    config: LoadBatchConfig,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    attempt = 0
    while True:
        try:
            return handler(batch)
        except RateLimitError as exc:
            if attempt >= config.retry_max:
                logger.warning("Rate limit retries exhausted for batch of %s record(s)", len(batch))
                return [], [
                    {
                        **record,
                        "_error": str(exc),
                        "_rate_limited": True,
                        "_retries_exhausted": True,
                    }
                    for record in batch
                ]
            delay = exc.retry_after
            if delay is None:
                delay = config.retry_base_seconds * (2**attempt)
            delay = min(delay, 60.0)
            logger.info(
                "Rate limited — retrying batch (%s records) in %.1fs (attempt %s/%s)",
                len(batch),
                delay,
                attempt + 1,
                config.retry_max,
            )
            time.sleep(delay)
            attempt += 1
