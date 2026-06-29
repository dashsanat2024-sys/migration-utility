"""AI-assisted lookup table generation from sample values vs Kraken enums."""

from __future__ import annotations

from typing import Any

from migration_utility.ai.heuristic import suggest_lookups_heuristic
from migration_utility.ai.models import LookupTableSuggestion
from migration_utility.ai.provider import get_chat_model, provider_mode


class AiLookupService:
    def suggest_lookups(
        self,
        mapping_rows: list[dict[str, Any]],
        column_samples: dict[str, list[str]],
    ) -> LookupTableSuggestion:
        if provider_mode() == "langchain":
            llm_result = self._llm_suggest(mapping_rows, column_samples)
            if llm_result.gaps:
                return llm_result
        return suggest_lookups_heuristic(mapping_rows, column_samples)

    def _llm_suggest(
        self,
        mapping_rows: list[dict[str, Any]],
        column_samples: dict[str, list[str]],
    ) -> LookupTableSuggestion:
        llm = get_chat_model()
        if llm is None:
            return LookupTableSuggestion()

        enum_rows = []
        for row in mapping_rows:
            if not row.get("source_field") or not row.get("target_field"):
                continue
            constraints = row.get("target_constraints") or {}
            if not constraints.get("enum"):
                continue
            src = row["source_field"]
            distinct = column_samples.get(src) or row.get("sample_values") or []
            enum_rows.append(
                {
                    "source_field": src,
                    "target_field": row["target_field"],
                    "enum_name": constraints.get("enum_name"),
                    "enum_values": constraints.get("enum"),
                    "source_distinct_values": distinct,
                }
            )
        if not enum_rows:
            return LookupTableSuggestion(summary="No enum-mapped fields to analyze")

        prompt = f"""For each row, propose a lookup map from source distinct values to valid Kraken enum values.
Flag unmapped source values. Only propose mappings you are confident about.

Rows:
{enum_rows}
"""
        try:
            structured = llm.with_structured_output(LookupTableSuggestion)
            return structured.invoke(prompt)
        except Exception:
            return LookupTableSuggestion()
