"""Tests for destination load batching, rate limits, and retry."""

from unittest.mock import MagicMock, patch

from migration_utility.connectors.kraken import KrakenClient
from migration_utility.connectors.load_executor import (
    LoadBatchConfig,
    RateLimitError,
    chunk_records,
    is_rate_limited_http,
    run_batched_load,
)


def test_chunk_records_splits_by_size():
    records = [{"id": str(i)} for i in range(5)]
    batches = chunk_records(records, 2)
    assert len(batches) == 3
    assert len(batches[0]) == 2
    assert len(batches[-1]) == 1


def test_is_rate_limited_http_detects_429_and_kt_code():
    assert is_rate_limited_http(429, "Too many requests")
    assert is_rate_limited_http(400, "Error KT-CT-1199: rate limit exceeded")
    assert not is_rate_limited_http(400, "KT-CT-10006: Account not found")


def test_run_batched_load_invokes_handler_per_batch():
    calls: list[int] = []

    def handler(batch: list[dict]) -> tuple[list, list]:
        calls.append(len(batch))
        return batch, []

    records = [{"id": str(i)} for i in range(5)]
    loaded, failed = run_batched_load(
        records,
        handler,
        config=LoadBatchConfig(batch_size=2, concurrency=1, max_rps=0, retry_max=0),
    )
    assert calls == [2, 2, 1]
    assert len(loaded) == 5
    assert failed == []


def test_run_batched_load_retries_rate_limit():
    attempts = {"n": 0}

    def handler(batch: list[dict]) -> tuple[list, list]:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RateLimitError("KT-CT-1199", retry_after=0.01)
        return batch, []

    records = [{"id": "1"}]
    loaded, failed = run_batched_load(
        records,
        handler,
        config=LoadBatchConfig(batch_size=10, concurrency=1, max_rps=0, retry_max=2, retry_base_seconds=0.01),
    )
    assert attempts["n"] == 2
    assert len(loaded) == 1
    assert failed == []


def test_run_batched_load_marks_batch_failed_when_retries_exhausted():
    def handler(_batch: list[dict]) -> tuple[list, list]:
        raise RateLimitError("KT-CT-1199")

    records = [{"id": "A"}, {"id": "B"}]
    loaded, failed = run_batched_load(
        records,
        handler,
        config=LoadBatchConfig(batch_size=10, concurrency=1, max_rps=0, retry_max=1, retry_base_seconds=0.01),
    )
    assert loaded == []
    assert len(failed) == 2
    assert all(f["_rate_limited"] for f in failed)


def test_kraken_mock_import_batches_records():
    client = KrakenClient(mock=True)
    records = [
        {"accountId": f"ACC-{i:03d}", "accountName": f"Co {i}", "accountStatus": "ACTIVE"}
        for i in range(5)
    ]
    config = LoadBatchConfig(batch_size=2, concurrency=2, max_rps=0, retry_max=0)
    loaded, failed = client.import_accounts(
        records,
        project_id="proj-1",
        environment="dev",
        load_config=config,
    )
    assert len(loaded) == 5
    assert failed == []


def test_kraken_live_import_retries_on_429():
    client = KrakenClient(mock=False, base_url="https://kraken.test")
    records = [{"accountId": "ACC-001", "accountName": "Test", "accountStatus": "ACTIVE"}]

    responses = [
        MagicMock(status_code=429, text="rate limited", headers={"Retry-After": "0.01"}),
        MagicMock(
            status_code=200,
            text='{"loaded":[{"accountId":"ACC-001"}],"failed":[]}',
            headers={},
        ),
    ]
    responses[1].json.return_value = {"loaded": [{"accountId": "ACC-001"}], "failed": []}

    with patch("migration_utility.connectors.kraken.post_json", side_effect=responses):
        loaded, failed = client.import_accounts(
            records,
            project_id="proj-1",
            load_config=LoadBatchConfig(
                batch_size=10,
                concurrency=1,
                max_rps=0,
                retry_max=2,
                retry_base_seconds=0.01,
            ),
        )

    assert len(loaded) == 1
    assert failed == []
