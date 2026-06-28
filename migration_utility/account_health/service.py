"""Account health assessment and cohort readiness scoring."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.account_health.checks import CHECKS_BY_ID, DEFAULT_HEALTH_CHECKS
from migration_utility.datastore.models import AccountHealthAssessment, AccountHealthRecord, Project
from migration_utility.datastore.session import get_engine
from migration_utility.ingest.staging import fetch_staged_rows, staging_table_name
from migration_utility.kraken.errors.classifier import classify_validation_finding
from migration_utility.plugins.registry import build_default_plugin_registry


def _external_id(record: dict[str, Any]) -> str:
    for key in ("number", "accountId", "account_id", "CUST_ACCOUNT_NO", "external_id", "id"):
        if record.get(key) not in (None, ""):
            return str(record[key])
    return "unknown"


def _readiness_status(score: int, has_blocker: bool) -> str:
    if has_blocker or score < 60:
        return "blocked"
    if score < 85:
        return "conditional"
    return "ready"


class AccountHealthService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def assess_project(
        self,
        project: Project,
        *,
        entity: str = "account",
        limit: int | None = None,
    ) -> AccountHealthAssessment:
        table = staging_table_name(project.slug, entity)
        rows = fetch_staged_rows(
            get_engine(),
            table,
            project_id=project.id,
            status="staged",
        )
        if limit:
            rows = rows[:limit]

        ctx = self._build_context(project, entity)
        ctx["_seen_accounts"] = set()

        records_out: list[dict[str, Any]] = []
        counts = {"ready": 0, "conditional": 0, "blocked": 0}
        blocker_by_category: dict[str, int] = {}
        kraken_code_hits: dict[str, int] = {}

        for idx, row in enumerate(rows, start=1):
            payload = {k: v for k, v in row.items() if not str(k).startswith("_")}
            findings: list[dict[str, Any]] = []
            score = 100
            has_blocker = False

            for check in DEFAULT_HEALTH_CHECKS:
                msg = check.evaluate(payload, ctx)
                if not msg:
                    continue
                classification = classify_validation_finding(check.id, msg)
                finding = {
                    "check_id": check.id,
                    "label": check.label,
                    "kind": check.kind,
                    "severity": check.severity,
                    "message": msg,
                    **classification,
                }
                findings.append(finding)
                score = max(0, score - check.weight)
                if check.severity == "blocker" or classification.get("is_blocker"):
                    has_blocker = True
                    cat = classification.get("root_cause_category", "unknown")
                    blocker_by_category[cat] = blocker_by_category.get(cat, 0) + 1
                for code in classification.get("kraken_error_codes") or []:
                    kraken_code_hits[code] = kraken_code_hits.get(code, 0) + 1

            status = _readiness_status(score, has_blocker)
            counts[status] += 1
            records_out.append(
                {
                    "row_number": idx,
                    "external_id": _external_id(payload),
                    "readiness_score": score,
                    "readiness_status": status,
                    "findings": findings,
                    "payload_snapshot": payload,
                    "has_blocker": has_blocker,
                }
            )

        total = len(records_out)
        cohort_score = round(sum(r["readiness_score"] for r in records_out) / total, 1) if total else 0.0

        assessment = AccountHealthAssessment(
            project_id=project.id,
            entity=entity,
            row_count=total,
            cohort_readiness_score=cohort_score,
            summary={
                "counts": counts,
                "blocker_by_root_cause": blocker_by_category,
                "top_kraken_codes_predicted": sorted(
                    kraken_code_hits.items(), key=lambda x: -x[1]
                )[:20],
                "checks_run": [c.id for c in DEFAULT_HEALTH_CHECKS],
                "strategy": "static_data_and_operational_blockers",
            },
        )
        self._db.add(assessment)
        self._db.flush()

        for rec in records_out:
            self._db.add(
                AccountHealthRecord(
                    assessment_id=assessment.id,
                    project_id=project.id,
                    external_id=rec["external_id"],
                    row_number=rec["row_number"],
                    readiness_score=rec["readiness_score"],
                    readiness_status=rec["readiness_status"],
                    findings=rec["findings"],
                    payload_snapshot=rec["payload_snapshot"],
                    has_blocker=rec["has_blocker"],
                )
            )

        self._db.flush()
        return assessment

    def _build_context(self, project: Project, entity: str) -> dict[str, Any]:
        ctx: dict[str, Any] = {"entity": entity}
        try:
            plugin = build_default_plugin_registry().resolve_for_project(project)
            if plugin:
                schema = plugin.get_schema(entity)
                ctx["required_fields"] = [f.name for f in schema.fields if f.required]
        except Exception:
            ctx["required_fields"] = ["number", "accountType", "status", "balance"]
        return ctx

    def latest_assessment(self, project_id: UUID, *, entity: str = "account") -> AccountHealthAssessment | None:
        return self._db.scalar(
            select(AccountHealthAssessment)
            .where(AccountHealthAssessment.project_id == project_id, AccountHealthAssessment.entity == entity)
            .order_by(AccountHealthAssessment.created_at.desc())
            .limit(1)
        )

    def list_records(
        self,
        assessment_id: UUID,
        *,
        status: str | None = None,
        limit: int = 500,
    ) -> list[AccountHealthRecord]:
        stmt = select(AccountHealthRecord).where(AccountHealthRecord.assessment_id == assessment_id)
        if status:
            stmt = stmt.where(AccountHealthRecord.readiness_status == status)
        stmt = stmt.order_by(AccountHealthRecord.readiness_score.asc()).limit(limit)
        return list(self._db.scalars(stmt))
