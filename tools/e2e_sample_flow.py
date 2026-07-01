#!/usr/bin/env python3
"""End-to-end smoke test using bundled sample files.

Flow:
  1. Utility mapping — target_cmp_ai_gap_sample.csv (field catalog + Kraken mappings)
  2. Runnable pipeline — accounts.csv (canonical ingest schema + migration run)

Usage:
  python tools/e2e_sample_flow.py
  API_BASE=https://migration-utility.vercel.app/api python tools/e2e_sample_flow.py
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
MAPPING_SAMPLE = ROOT / "samples" / "severn_trent" / "target_cmp_ai_gap_sample.csv"
INGEST_SAMPLE = ROOT / "samples" / "accounts.csv"
API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000/api").rstrip("/")


def fail(msg: str, resp: httpx.Response | None = None) -> None:
    detail = f" — {resp.status_code} {resp.text[:400]}" if resp is not None else ""
    print(f"FAIL: {msg}{detail}", file=sys.stderr)
    sys.exit(1)


def ok(step: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"OK  {step}{suffix}")


def upload_source(client: httpx.Client, project_id: str, path: Path) -> int:
    with path.open("rb") as fh:
        resp = client.post(
            f"/projects/{project_id}/fields/account/source",
            files={"file": (path.name, fh, "text/csv")},
        )
    if resp.status_code != 200:
        fail(f"upload source fields ({path.name})", resp)
    return len(resp.json().get("source_fields", []))


def suggest_mapped(client: httpx.Client, project_id: str) -> list[dict]:
    resp = client.post(
        f"/projects/{project_id}/fields/account/suggest-mappings",
        params={"destination_first": "true"},
    )
    if resp.status_code != 200:
        fail("suggest mappings", resp)
    suggestions = resp.json()
    return [s for s in suggestions if s.get("source_field") and s.get("target_field")]


def create_draft_rule_set(client: httpx.Client, project_id: str, slug: str, label: str) -> str:
    resp = client.post(
        f"/projects/{project_id}/rules",
        json={"entity": "account", "name": f"{label} {slug}"},
    )
    if resp.status_code != 201:
        fail(f"create rule set ({label})", resp)
    return resp.json()["id"]


def apply_mappings(client: httpx.Client, project_id: str, rule_set_id: str, mapped: list[dict]) -> None:
    mappings = [
        {
            "source_field": row["source_field"],
            "target_field": row["target_field"],
            "transform_type": row.get("transform_type") or "copy",
            "config": row.get("config") or {},
            "enabled": True,
        }
        for row in mapped
    ]
    if not mappings:
        fail("no mappings to apply")
    resp = client.post(
        f"/projects/{project_id}/fields/account/apply-mappings/{rule_set_id}",
        json={"mappings": mappings},
    )
    if resp.status_code != 204:
        fail("apply mappings", resp)


def upload_ingest(client: httpx.Client, project_id: str, path: Path) -> dict:
    with path.open("rb") as fh:
        resp = client.post(
            f"/projects/{project_id}/ingest/upload",
            data={"entity": "account"},
            files={"file": (path.name, fh, "text/csv")},
        )
    if resp.status_code != 201:
        fail(f"ingest upload ({path.name})", resp)
    return resp.json()


def main() -> None:
    for path in (MAPPING_SAMPLE, INGEST_SAMPLE):
        if not path.is_file():
            fail(f"Sample file missing: {path}")

    slug = f"e2e-{uuid.uuid4().hex[:8]}"
    with httpx.Client(base_url=API_BASE, timeout=120.0) as client:
        health = client.get("/health")
        if health.status_code != 200:
            fail("health check", health)
        ok("health", f"v{health.json().get('version', '?')}")

        project = client.post(
            "/projects",
            json={
                "name": f"E2E Sample {slug}",
                "slug": slug,
                "description": "Automated E2E — utility mapping + accounts ingest",
                "target_system": "kraken",
                "source_connector_key": "staging",
                "target_adapter_key": "kraken",
                "environment": "dev",
                "config": {
                    "profile": {
                        "migration_type": "data_migration",
                        "industry": "utility",
                        "integration_approach": "api",
                        "features": {
                            "tariff_mapping": True,
                            "transform_rules": True,
                            "validation_rules": True,
                        },
                    }
                },
            },
        )
        if project.status_code != 201:
            fail("create project", project)
        project_id = project.json()["id"]
        ok("create project", slug)

        workspace = client.get(f"/projects/{slug}/workspace", params={"entity": "account"})
        if workspace.status_code != 200:
            fail("workspace", workspace)
        ok("workspace", "Kraken destination schema loaded")

        # --- Utility mapping track (Target/CMP sample) ---
        n = upload_source(client, project_id, MAPPING_SAMPLE)
        ok("utility source fields", f"{n} columns from {MAPPING_SAMPLE.name}")

        utility_mapped = suggest_mapped(client, project_id)
        ok("utility suggest mappings", f"{len(utility_mapped)} mapped")

        utility_rs = create_draft_rule_set(client, project_id, slug, "Utility mappings")
        apply_mappings(client, project_id, utility_rs, utility_mapped)
        ok("utility apply mappings", str(len(utility_mapped)))

        # --- Runnable pipeline (canonical accounts sample) ---
        n = upload_source(client, project_id, INGEST_SAMPLE)
        ok("run source fields", f"{n} columns from {INGEST_SAMPLE.name}")

        run_mapped = suggest_mapped(client, project_id)
        if not run_mapped:
            run_mapped = [
                {"source_field": "id", "target_field": "number", "transform_type": "copy", "config": {}},
                {"source_field": "name", "target_field": "billingName", "transform_type": "copy", "config": {}},
                {
                    "source_field": "status",
                    "target_field": "status",
                    "transform_type": "lookup",
                    "config": {"map": {"active": "ACTIVE", "inactive": "INACTIVE"}},
                },
            ]
        ok("run suggest mappings", f"{len(run_mapped)} mapped")

        run_rs = create_draft_rule_set(client, project_id, slug, "Run mappings")
        apply_mappings(client, project_id, run_rs, run_mapped)
        ok("run apply mappings", str(len(run_mapped)))

        ingest_body = upload_ingest(client, project_id, INGEST_SAMPLE)
        staged = ingest_body.get("staged_count", 0)
        errors = ingest_body.get("error_count", 0)
        ok("ingest & stage", f"{staged} staged, {errors} errors")
        if staged == 0:
            fail("no rows staged — cannot run migration")

        stats = client.get(f"/projects/{project_id}/ingest/staging/account/stats")
        if stats.status_code != 200:
            fail("staging stats", stats)
        ok("staging stats", f"{stats.json().get('row_count', 0)} rows")

        run = client.post(
            f"/projects/{project_id}/runs",
            json={
                "name": f"E2E run {slug}",
                "run_config": {
                    "entity": "account",
                    "use_rules": True,
                    "use_selection": False,
                    "rule_set_id": run_rs,
                },
                "batches": [{"batch_number": 1}],
            },
        )
        if run.status_code != 201:
            fail("create run", run)
        run_id = run.json()["id"]
        run_status = run.json().get("status", "?")
        ok("create run", f"status={run_status}")

        for _ in range(45):
            progress = client.get(f"/runs/{run_id}/progress")
            if progress.status_code != 200:
                fail("run progress", progress)
            body = progress.json()
            status = body.get("status")
            if status in ("completed", "failed", "cancelled"):
                run_status = status
                break
            time.sleep(2)
        else:
            fail("run did not finish within timeout")

        loads = client.get(f"/runs/{run_id}/loads")
        load_count = len(loads.json()) if loads.status_code == 200 else 0
        ok("run finished", f"status={run_status}, destination loads={load_count}")

        if run_status != "completed":
            detail = client.get(f"/runs/{run_id}")
            msg = detail.json().get("error_message", "") if detail.status_code == 200 else ""
            fail(f"run status {run_status}" + (f": {msg}" if msg else ""), detail if detail.status_code != 200 else None)

        ui_base = (
            "https://migration-utility.vercel.app"
            if "vercel.app" in API_BASE
            else "http://127.0.0.1:5174"
        )
        print(f"\nE2E passed — project: {slug}")
        print(f"UI: {ui_base}/projects/{slug}")
        print(f"Mapping sample: {MAPPING_SAMPLE.name}")
        print(f"Ingest sample:  {INGEST_SAMPLE.name}")


if __name__ == "__main__":
    main()
