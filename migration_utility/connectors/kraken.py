from __future__ import annotations

import json
import uuid
from typing import Any

from migration_utility.config import get_settings
from migration_utility.connectors.base import TargetAdapter
from migration_utility.connectors.target_validation import validate_against_target
from migration_utility.core.events import RunContext


class KrakenClient:
    """HTTP-style client for Kraken migration APIs (mock by default)."""

    def __init__(self, *, base_url: str | None = None, mock: bool = True) -> None:
        settings = get_settings()
        self._base_url = base_url or settings.kraken_api_url
        self._mock = mock or settings.kraken_mock_mode

    def import_accounts(
        self,
        records: list[dict[str, Any]],
        *,
        project_id: str,
        environment: str = "dev",
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if self._mock:
            return self._mock_import(records, project_id=project_id, environment=environment)
        raise NotImplementedError("Live Kraken API calls require kraken_mock_mode=false and credentials")

    def import_products(
        self,
        records: list[dict[str, Any]],
        *,
        project_id: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if self._mock:
            loaded = [
                {
                    **record,
                    "importStatus": "accepted",
                    "krakenProductId": f"PRD-{uuid.uuid4().hex[:8].upper()}",
                    "projectId": project_id,
                }
                for record in records
            ]
            return loaded, []
        raise NotImplementedError("Live Kraken product import not configured")

    def _mock_import(
        self,
        records: list[dict[str, Any]],
        *,
        project_id: str,
        environment: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        loaded: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        for record in records:
            account_id = record.get("accountId") or record.get("id")
            if not account_id:
                failed.append({**record, "_error": "Missing accountId"})
                continue
            loaded.append(
                {
                    **record,
                    "krakenAccountId": f"KRA-{account_id}",
                    "importStatus": "accepted",
                    "environment": environment,
                    "projectId": project_id,
                }
            )
        return loaded, failed


class KrakenTargetAdapter(TargetAdapter):
    """Loads transformed account payloads into Kraken (mock migration API)."""

    key = "kraken"

    def __init__(self, client: KrakenClient | None = None) -> None:
        self._client = client or KrakenClient()

    def validate_target_payload(
        self,
        records: list[dict[str, Any]],
        ctx: RunContext,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        target_system = ctx.metadata.get("target_system", "kraken")
        entity = ctx.config.get("entity", "account")
        return validate_against_target(records, target_system=target_system, entity=entity)

    def load(
        self,
        records: list[dict[str, Any]],
        ctx: RunContext,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        valid, invalid = self.validate_target_payload(records, ctx)
        if not valid:
            return [], invalid

        environment = ctx.config.get("environment", ctx.metadata.get("environment", "dev"))
        project_id = str(ctx.project_id)
        loaded, failed = self._client.import_accounts(
            valid,
            project_id=project_id,
            environment=environment,
        )
        return loaded, invalid + failed


class KrakenProductImportAdapter:
    """Tariff/product import used by tariff load workflow."""

    key = "kraken_product_import"

    def __init__(self, client: KrakenClient | None = None) -> None:
        self._client = client or KrakenClient()

    def import_products(
        self,
        records: list[dict[str, Any]],
        *,
        project_id: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        return self._client.import_products(records, project_id=project_id)
