"""AI-assisted transform rule suggestions from source sample values."""

from __future__ import annotations

from typing import Any

from migration_utility.ai.heuristic import suggest_lookups_heuristic


def _normalize(v: Any) -> str:
    return str(v or "").strip()


def _distinct_values(values: list[Any]) -> list[str]:
    seen: list[str] = []
    for raw in values:
        v = _normalize(raw)
        if not v or v in seen:
            continue
        seen.append(v)
    return seen


def _is_boolean_flag(values: list[str]) -> bool:
    lowered = {v.lower() for v in values}
    return lowered in ({"y", "n"}, {"true", "false"}, {"1", "0"}, {"t", "f"}, {"yes", "no"})


def _boolean_lookup(values: list[str]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for v in values:
        lv = v.lower()
        if lv in {"y", "true", "1", "t", "yes"}:
            lookup[v] = "true"
        elif lv in {"n", "false", "0", "f", "no"}:
            lookup[v] = "false"
    return lookup


def _maybe_date(values: list[str]) -> bool:
    # Keep this intentionally strict: only infer format-based date transforms for ISO-like values.
    return bool(values) and all(len(v) == 10 and v[4] == "-" and v[7] == "-" for v in values)


def _enum_lookup(distinct: list[str], enum_values: list[str]) -> tuple[dict[str, str], list[str]]:
    enum_by_upper = {str(v).upper(): str(v) for v in enum_values}
    mapping: dict[str, str] = {}
    uncovered: list[str] = []
    for value in distinct:
        direct = enum_by_upper.get(value.upper())
        if direct:
            mapping[value] = direct
            continue
        uncovered.append(value)
    return mapping, uncovered


class AiTransformRuleService:
    """Suggest transform rules from source samples + destination constraints."""

    def suggest_transform_rules(
        self,
        mapping_rows: list[dict[str, Any]],
        column_samples: dict[str, list[str]],
    ) -> list[dict[str, Any]]:
        lookup_gaps = suggest_lookups_heuristic(mapping_rows, column_samples)
        gap_by_target = {g.target_field: g for g in lookup_gaps.gaps}

        out: list[dict[str, Any]] = []
        for row in mapping_rows:
            source = row.get("source_field")
            target = row.get("target_field")
            if not source or not target:
                out.append(row)
                continue

            constraints = row.get("target_constraints") or {}
            distinct = _distinct_values(column_samples.get(source) or row.get("sample_values") or [])
            target_type = str(row.get("target_type") or "").lower()
            enum_values = constraints.get("enum") or []

            updated = dict(row)
            updated.setdefault("config", {})
            updated["uncovered_source_values"] = []

            if enum_values:
                direct_map, uncovered = _enum_lookup(distinct, enum_values)
                gap = gap_by_target.get(target)
                proposed_gap_map = gap.proposed_lookup if gap else {}
                lookup_map = {**direct_map, **proposed_gap_map}
                if lookup_map:
                    updated["transform_type"] = "lookup"
                    updated["config"] = {"map": lookup_map, "default": ""}
                    updated["ai_suggested"] = True
                    updated["confidence_score"] = 0.9 if not uncovered else 0.65
                    updated["ai_reasoning"] = (
                        f"Inferred enum lookup for {source} → {target}; "
                        f"{len(lookup_map)} value(s) mapped from sample data."
                    )
                    updated["uncovered_source_values"] = sorted(uncovered)
                out.append(updated)
                continue

            if target_type in {"boolean", "bool"} and len(distinct) <= 2 and _is_boolean_flag(distinct):
                bool_map = _boolean_lookup(distinct)
                updated["transform_type"] = "conditional"
                updated["config"] = {"map": bool_map, "default": "false"}
                updated["ai_suggested"] = True
                updated["confidence_score"] = 0.97
                updated["ai_reasoning"] = (
                    f"Detected boolean flag values {distinct}; proposing conditional Y/N-style transform."
                )
                out.append(updated)
                continue

            if _maybe_date(distinct):
                updated["transform_type"] = "date_format"
                updated["config"] = {"input_format": "YYYY-MM-DD", "output_format": "YYYY-MM-DD"}
                updated["ai_suggested"] = True
                updated["confidence_score"] = 0.8
                updated["ai_reasoning"] = "Sample values look like ISO dates; proposing date_reformat transform."
                out.append(updated)
                continue

            out.append(updated)
        return out
