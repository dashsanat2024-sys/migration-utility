"""LangChain structured mapping suggestions."""

from __future__ import annotations

import json
from typing import Any

from migration_utility.ai.models import MappingSuggestion
from migration_utility.ai.provider import get_chat_model


def llm_suggest_for_target(
    target_field: dict[str, Any],
    source_fields: list[dict[str, Any]],
    *,
    used_sources: set[str],
) -> tuple[dict[str, Any] | None, MappingSuggestion | None]:
    llm = get_chat_model()
    if llm is None:
        return None, None

    available = [sf for sf in source_fields if sf["name"] not in used_sources]
    if not available:
        return None, None

    constraints = target_field.get("constraints") or {}
    enum_values = constraints.get("enum")

    prompt = f"""You are a data migration mapping assistant. Suggest ONE source column for this destination field.
Return structured JSON only. Never guess if semantic distance is too large — set no_match=true.

Destination field: {target_field['name']}
Type: {target_field.get('data_type', 'string')}
Required: {target_field.get('required', False)}
Description: {target_field.get('description', '')}
Enum values: {json.dumps(enum_values) if enum_values else 'none'}

Source columns (name, type, sample values):
{json.dumps([{'name': s['name'], 'type': s.get('data_type'), 'samples': (s.get('sample_values') or [])[:8]} for s in available], indent=2)}
"""

    try:
        structured = llm.with_structured_output(MappingSuggestion)
        result: MappingSuggestion = structured.invoke(prompt)
    except Exception:
        return None, None

    if result.no_match or not result.destination_field:
        return None, result

    src = next((s for s in available if s["name"] in result.reasoning), None)
    if src is None:
        # Match by best name overlap
        dest_key = target_field["name"].lower()
        for s in available:
            if s["name"].lower() in result.reasoning.lower():
                src = s
                break
        if src is None and len(available) == 1:
            src = available[0]
    return src, result
