from __future__ import annotations

import uuid
from typing import Any

from migration_utility.config import get_settings
from migration_utility.connectors.base import TargetAdapter
from migration_utility.connectors.target_validation import validate_against_target
from migration_utility.core.events import RunContext


class SapClient:
    """SAP customer master import client (mock IDoc/BAPI by default)."""

    def __init__(self, *, base_url: str | None = None, mock: bool = True) -> None:
        settings = get_settings()
        self._base_url = base_url or settings.sap_api_url
        self._mock = mock or settings.sap_mock_mode

    def post_customers(
        self,
        records: list[dict[str, Any]],
        *,
        project_id: str,
        idoc_type: str = "DEBMAS01",
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if self._mock:
            return self._mock_post(records, project_id=project_id, idoc_type=idoc_type)
        raise NotImplementedError("Live SAP integration requires sap_mock_mode=false")

    def _mock_post(
        self,
        records: list[dict[str, Any]],
        *,
        project_id: str,
        idoc_type: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        loaded: list[dict[str, Any]] = []
        failed: list[dict[str, Any]] = []
        for record in records:
            kunnr = record.get("KUNNR") or record.get("accountId") or record.get("id")
            if not kunnr:
                failed.append({**record, "_error": "Missing customer number (KUNNR/accountId)"})
                continue
            loaded.append(
                {
                    **record,
                    "sapCustomerNumber": str(kunnr).zfill(10),
                    "idocType": idoc_type,
                    "idocNumber": f"IDOC-{uuid.uuid4().hex[:10].upper()}",
                    "status": "posted",
                    "projectId": project_id,
                }
            )
        return loaded, failed


class SapTargetAdapter(TargetAdapter):
    """Loads customer master data into SAP via mock IDoc posting."""

    key = "sap"

    def __init__(self, client: SapClient | None = None) -> None:
        self._client = client or SapClient()

    def validate_target_payload(
        self,
        records: list[dict[str, Any]],
        ctx: RunContext,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        target_system = ctx.metadata.get("target_system", "sap")
        entity = ctx.config.get("entity", "account")
        valid, invalid = validate_against_target(records, target_system=target_system, entity=entity)
        if valid:
            return [self._to_sap_record(r) for r in valid], invalid
        return valid, invalid

    def load(
        self,
        records: list[dict[str, Any]],
        ctx: RunContext,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        sap_records = [self._to_sap_record(r) for r in records]
        valid, invalid = self.validate_target_payload(sap_records, ctx)
        if not valid:
            return [], invalid

        idoc_type = ctx.config.get("sap_idoc_type", "DEBMAS01")
        loaded, failed = self._client.post_customers(
            valid,
            project_id=str(ctx.project_id),
            idoc_type=idoc_type,
        )
        return loaded, invalid + failed

    @staticmethod
    def _to_sap_record(record: dict[str, Any]) -> dict[str, Any]:
        return {
            "KUNNR": record.get("KUNNR") or record.get("accountId") or record.get("id"),
            "NAME1": record.get("NAME1") or record.get("accountName") or record.get("name"),
            "STATUS": record.get("STATUS") or record.get("accountStatus") or record.get("status"),
        }
