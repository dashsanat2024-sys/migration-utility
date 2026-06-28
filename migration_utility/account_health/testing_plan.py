"""Migration testing plan templates (mapping, product-build, dress rehearsal)."""

from __future__ import annotations

from typing import Any


def build_testing_plan(*, target_system: str = "kraken") -> dict[str, Any]:
    return {
        "target_system": target_system,
        "phases": [
            {
                "id": "mapping_validation",
                "label": "Mapping validation",
                "description": "Verify every source field maps to a valid Kraken socket; run transform preview on sample rows.",
                "required": True,
                "artifacts": ["field_catalog", "mapping_matrix", "transform_preview_samples"],
            },
            {
                "id": "product_build_validation",
                "label": "Product-build validation",
                "description": "Validate tariff/product codes exist in destination; seed tariff mappings and dry-run product import.",
                "required": True,
                "artifacts": ["tariff_mapping_set", "product_import_dry_run"],
            },
            {
                "id": "account_health_gate",
                "label": "Account health gate",
                "description": "Run cohort readiness assessment; resolve blockers before migration wave.",
                "required": True,
                "artifacts": ["account_health_assessment", "fallout_queue_empty_blockers"],
            },
            {
                "id": "ai_led_testing",
                "label": "AI-led testing opportunities",
                "description": "Use profiling anomalies + predicted Kraken codes to generate targeted test cases and edge-case payloads.",
                "required": False,
                "artifacts": ["anomaly_report", "kraken_code_coverage_matrix"],
            },
            {
                "id": "parallel_bill_validation",
                "label": "Parallel bill validation (optional)",
                "description": "Compare legacy vs Kraken bill estimates for a sample cohort before cutover.",
                "required": False,
                "artifacts": ["bill_comparison_sample"],
            },
            {
                "id": "volume_testing",
                "label": "Volume testing",
                "description": "Load test with worker mode at production chunk sizes; monitor rate limits (KT-CT-1199).",
                "required": True,
                "artifacts": ["volume_test_run", "worker_progress_metrics"],
            },
            {
                "id": "dress_rehearsal",
                "label": "Dress rehearsal (pre-prod)",
                "description": "Full pipeline in pre-production Kraken environment with production-like volume subset.",
                "required": True,
                "artifacts": ["preprod_run_audit", "reconciliation_report", "exception_resolution_log"],
            },
        ],
        "exit_criteria": [
            "Cohort readiness score ≥ 85% with zero operational blockers",
            "All mapping rules signed off",
            "Fallout queue blockers assigned and remediated or waived",
            "Dress rehearsal reconciliation within agreed variance threshold",
        ],
    }
