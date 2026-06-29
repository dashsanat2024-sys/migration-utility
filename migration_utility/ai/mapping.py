"""AI-assisted field mapping — baseline deterministic + semantic upgrade."""

from __future__ import annotations

from typing import Any

from migration_utility.ai.heuristic import apply_enum_lookup_transforms, enrich_schema_mappings, heuristic_mapping_for_target
from migration_utility.ai.llm_mapping import llm_suggest_for_target
from migration_utility.ai.provider import provider_mode
from migration_utility.fields.catalog_parser import suggest_schema_mappings


class AiMappingService:
    def suggest_schema_mappings(
        self,
        source_fields: list[dict[str, Any]],
        destination_fields: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        baseline = suggest_schema_mappings(source_fields, destination_fields)
        mode = provider_mode()

        if mode == "langchain":
            rows = self._llm_enrich(baseline, source_fields, destination_fields)
        elif mode == "heuristic":
            rows = enrich_schema_mappings(baseline, source_fields, destination_fields)
        else:
            return baseline

        return apply_enum_lookup_transforms(rows, source_fields, destination_fields)

    def _llm_enrich(
        self,
        baseline: list[dict[str, Any]],
        source_fields: list[dict[str, Any]],
        destination_fields: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        dest_by_name = {d["name"]: d for d in destination_fields}
        used = {r["source_field"] for r in baseline if r.get("source_field")}
        out: list[dict[str, Any]] = []

        for row in baseline:
            if row.get("source_field") or not row.get("target_field"):
                out.append(row)
                continue
            dest = dest_by_name.get(row["target_field"])
            if not dest:
                out.append(row)
                continue

            src, suggestion = llm_suggest_for_target(dest, source_fields, used_sources=used)
            if src is None or suggestion is None or suggestion.no_match:
                # Fall back to heuristic for this row
                match = heuristic_mapping_for_target(dest, source_fields, used_sources=used)
                if match:
                    src, suggestion = match
                else:
                    out.append(row)
                    continue

            used.add(src["name"])
            config: dict[str, Any] = {}
            transform = suggestion.suggested_transform or "copy"
            if transform == "lookup" and suggestion.lookup_table:
                config = {"map": suggestion.lookup_table, "default": ""}

            out.append(
                {
                    **row,
                    "source_field": src["name"],
                    "source_type": src.get("data_type"),
                    "source_required": src.get("required", False),
                    "transform_type": transform,
                    "config": config,
                    "status": "mapped",
                    "match_confidence": _confidence_label(suggestion.confidence),
                    "confidence_score": suggestion.confidence,
                    "ai_suggested": True,
                    "ai_reasoning": suggestion.reasoning or f"LLM suggested {src['name']} → {dest['name']}",
                }
            )
        return out


def _confidence_label(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.65:
        return "medium"
    if score >= 0.45:
        return "low"
    return "none"
