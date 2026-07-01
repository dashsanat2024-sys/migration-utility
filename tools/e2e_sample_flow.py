#!/usr/bin/env python3
"""End-to-end smoke test using bundled Target/CMP sample extract.

Usage:
  python tools/e2e_sample_flow.py
  API_BASE=https://migration-utility.vercel.app/api python tools/e2e_sample_flow.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_CSV = ROOT / "samples" / "severn_trent" / "target_cmp_ai_gap_sample.csv"
API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000/api").rstrip("/")


def fail(msg: str, resp: httpx.Response | None = None) -> None:
    detail = f" — {resp.status_code} {resp.text[:400]}" if resp is not None else ""
    print(f"FAIL: {msg}{detail}", file=sys.stderr)
    sys.exit(1)


def ok(step: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"OK  {step}{suffix}")


def main() -> None:
    if not SAMPLE_CSV.is_file():
        fail(f"Sample file missing: {SAMPLE_CSV}")

    slug = f"e2e-{uuid.uuid4().hex[:8]}"
    with httpx.Client(base_url=API_BASE, timeout=120.0) as client:
        health = client.get("/health")
        if health.status_code != 200:
            fail("health check", health)
        version = health.json().get("version", "?")
        ok("health", f"v{version}")

        project = client.post(
            "/projects",
            json={
                "name": f"E2E Sample {slug}",
                "slug": slug,
                "description": "Automated E2E with target_cmp_ai_gap_sample.csv",
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
        ok("workspace", f"{len(workspace.json().get('destination_schema', {}).get('fields', []))} dest fields")

        with SAMPLE_CSV.open("rb") as fh:
            source_upload = client.post(
                f"/projects/{project_id}/fields/account/source",
                files={"file": (SAMPLE_CSV.name, fh, "text/csv")},
            )
        if source_upload.status_code != 200:
            fail("upload source field catalog", source_upload)
        field_count = len(source_upload.json().get("source_fields", []))
        ok("upload source fields", f"{field_count} columns")

        suggest = client.post(
            f"/projects/{project_id}/fields/account/suggest-mappings",
            params={"destination_first": "true"},
        )
        if suggest.status_code != 200:
            fail("suggest mappings", suggest)
        suggestions = suggest.json()
        mapped = [s for s in suggestions if s.get("source_field") and s.get("target_field")]
        ok("suggest mappings", f"{len(mapped)}/{len(suggestions)} mapped")

        rules = client.get(f"/projects/{project_id}/rules", params={"entity": "account"})
        if rules.status_code != 200:
            fail("list rule sets", rules)
        rule_sets = rules.json()
        if not rule_sets:
            fail("no rule set found for project")
        rule_set_id = rule_sets[0]["id"]

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

        apply_resp = client.post(
            f"/projects/{project_id}/fields/account/apply-mappings/{rule_set_id}",
            json={"mappings": mappings},
        )
        if apply_resp.status_code != 204:
            fail("apply mappings", apply_resp)
        ok("apply mappings", str(len(mappings)))

        with SAMPLE_CSV.open("rb") as fh:
            ingest = client.post(
                f"/projects/{project_id}/ingest/upload",
                data={"entity": "account"},
                files={"file": (SAMPLE_CSV.name, fh, "text/csv")},
            )
        if ingest.status_code != 201:
            fail("ingest upload", ingest)
        ingest_body = ingest.json()
        ok(
            "ingest & stage",
            f"{ingest_body.get('staged_count', 0)} staged, {ingest_body.get('error_count', 0)} errors",
        )

        stats = client.get(f"/projects/{project_id}/staging/account/stats")
        if stats.status_code != 200:
            fail("staging stats", stats)
        row_count = stats.json().get("row_count", 0)
        ok("staging stats", f"{row_count} rows")

        run = client.post(
            f"/projects/{project_id}/runs",
            json={
                "name": f"E2E run {slug}",
                "run_config": {"entity": "account", "use_rules": True, "use_selection": False},
                "batches": [{"batch_number": 1}],
            },
        )
        if run.status_code != 201:
            fail("create run", run)
        run_id = run.json()["id"]
        run_status = run.json().get("status", "?")
        ok("create run", f"id={run_id[:8]}… status={run_status}")

        for _ in range(30):
            progress = client.get(f"/runs/{run_id}/progress")
            if progress.status_code != 200:
                fail("run progress", progress)
            body = progress.json()
            status = body.get("status")
            pct = body.get("progress_pct", 0)
            if status in ("completed", "failed", "cancelled"):
                run_status = status
                break
            time.sleep(2)
        else:
            fail("run did not finish within timeout")

        loads = client.get(f"/runs/{run_id}/loads")
        load_count = len(loads.json()) if loads.status_code == 200 else 0
        ok("run finished", f"status={run_status}, loads={load_count}")

        if run_status != "completed":
            detail = client.get(f"/runs/{run_id}")
            fail(f"run status {run_status}", detail if detail.status_code == 200 else None)

        print(f"\nE2E passed — project slug: {slug}")
        print(f"Open: https://migration-utility.vercel.app/projects/{slug}")


if __name__ == "__main__":
    main()
