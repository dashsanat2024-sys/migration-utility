"""Fallout management — sync health findings and Kraken rejections to exception queue."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.datastore.models import AccountHealthRecord, ExceptionItem
from migration_utility.exceptions.service import ExceptionQueueService
from migration_utility.kraken.errors.classifier import classify_kraken_response, classify_validation_finding


class FalloutService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._exceptions = ExceptionQueueService(db)

    def sync_health_record(self, record: AccountHealthRecord, *, entity: str) -> ExceptionItem | None:
        if not record.has_blocker and record.readiness_status == "ready":
            return None

        primary = (record.findings or [{}])[0] if record.findings else {}
        check_id = primary.get("check_id", "account_health")
        classification = classify_validation_finding(check_id, primary.get("message", ""))

        existing = self._db.scalar(
            select(ExceptionItem).where(
                ExceptionItem.project_id == record.project_id,
                ExceptionItem.source_type == "account_health",
                ExceptionItem.row_number == record.row_number,
                ExceptionItem.status.in_(("open", "assigned", "overridden")),
            )
        )
        if existing:
            return existing

        item = ExceptionItem(
            project_id=record.project_id,
            entity=entity,
            source_type="account_health",
            row_number=record.row_number,
            payload={
                "external_id": record.external_id,
                "readiness_score": record.readiness_score,
                "findings": record.findings,
                **record.payload_snapshot,
            },
            error_reason=primary.get("message") or f"Account health: {record.readiness_status}",
            status="open",
            kraken_error_code=classification.get("primary_kraken_code"),
            root_cause_category=classification.get("root_cause_category"),
            owner_role=classification.get("owner_role"),
            remediation_hint=classification.get("remediation_hint"),
            fallout_status="open",
        )
        self._db.add(item)
        self._db.flush()
        return item

    def sync_assessment_fallout(
        self,
        project_id: UUID,
        assessment_id: UUID,
        *,
        entity: str,
        statuses: tuple[str, ...] = ("blocked", "conditional"),
    ) -> list[ExceptionItem]:
        records = list(
            self._db.scalars(
                select(AccountHealthRecord).where(
                    AccountHealthRecord.assessment_id == assessment_id,
                    AccountHealthRecord.readiness_status.in_(statuses),
                )
            )
        )
        items = []
        for rec in records:
            item = self.sync_health_record(rec, entity=entity)
            if item:
                items.append(item)
        self._db.commit()
        return items

    def classify_load_failure(self, payload: dict, *, entity: str, project_id: UUID, run_id: UUID | None) -> ExceptionItem:
        classification = classify_kraken_response(payload)
        error_text = (
            payload.get("_error")
            or payload.get("message")
            or classification.get("kraken_message")
            or "Kraken load failed"
        )
        item = ExceptionItem(
            project_id=project_id,
            run_id=run_id,
            entity=entity,
            source_type="kraken_load",
            payload=payload,
            error_reason=str(error_text)[:2000],
            status="open",
            kraken_error_code=classification.get("primary_kraken_code"),
            root_cause_category=classification.get("root_cause_category"),
            owner_role=classification.get("owner_role"),
            remediation_hint=classification.get("remediation_hint"),
            fallout_status="open",
        )
        self._db.add(item)
        self._db.flush()
        return item
