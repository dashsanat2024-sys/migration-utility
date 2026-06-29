"""Rule-based semantic fallback when LangChain is unavailable (CI / no API key)."""

from __future__ import annotations

from typing import Any

from migration_utility.ai.models import ErrorCluster, ErrorTriageReport, LookupGap, LookupTableSuggestion, MappingSuggestion
from migration_utility.fields.catalog_parser import normalize_field_key, suggest_schema_mappings
from migration_utility.kraken.errors.catalog import get_kraken_error_catalog

# Known CMP → Kraken enum lookup hints (semantic, not just name match).
_ENUM_LOOKUP_HINTS: dict[tuple[str, str], dict[str, str]] = {
    ("acctstatuscode", "status"): {
        "A": "ACTIVE",
        "P": "PENDING",
        "W": "WITHDRAWN",
        "D": "DORMANT",
        "ACTIVE": "ACTIVE",
        "PENDING": "PENDING",
    },
    ("custtypeflag", "accounttype"): {
        "O": "OCCUPIER",
        "D": "DOMESTIC",
        "B": "BUSINESS",
        "V": "VACANT",
        "M": "MANAGED",
    },
    ("commspref", "commsdeliverypreference"): {
        "E": "EMAIL",
        "P": "POSTAL_MAIL",
        "EMAIL": "EMAIL",
    },
}

# Fields where forcing a bad guess is worse than leaving unmapped.
_NO_GUESS_TARGETS = frozenset({"complaintflag", "complaint_flag"})


def heuristic_mapping_for_target(
    target_field: dict[str, Any],
    source_fields: list[dict[str, Any]],
    *,
    used_sources: set[str],
) -> tuple[dict[str, Any], MappingSuggestion] | None:
    dest_name = target_field["name"]
    dest_key = normalize_field_key(dest_name)
    constraints = target_field.get("constraints") or {}
    enum_values = constraints.get("enum") or []

    best: tuple[float, dict[str, Any]] | None = None
    for sf in source_fields:
        if sf["name"] in used_sources:
            continue
        src_key = normalize_field_key(sf["name"])
        if src_key in _NO_GUESS_TARGETS:
            continue
        score = 0.0
        if src_key == dest_key:
            score = 1.0
        elif dest_key in src_key or src_key in dest_key:
            score = 0.55
        hint = _ENUM_LOOKUP_HINTS.get((src_key, dest_key))
        if hint:
            score = max(score, 0.85)
        elif enum_values and sf.get("data_type") == "string":
            samples = sf.get("sample_values") or []
            if samples and all(str(v).upper() in {str(e).upper() for e in enum_values} for v in samples[:5]):
                score = max(score, 0.75)
        if score >= 0.5 and (best is None or score > best[0]):
            best = (score, sf)

    if not best:
        return None

    score, sf = best
    src_key = normalize_field_key(sf["name"])
    dest_key = normalize_field_key(dest_name)
    lookup = _ENUM_LOOKUP_HINTS.get((src_key, dest_key))
    transform = "lookup" if lookup else "copy"
    reasoning = f"Heuristic: {sf['name']} → {dest_name} (score {score:.2f})"
    if lookup:
        reasoning += f"; enum lookup table with {len(lookup)} value(s)"
    suggestion = MappingSuggestion(
        destination_field=dest_name,
        confidence=score,
        suggested_transform=transform,
        lookup_table=lookup,
        reasoning=reasoning,
    )
    return sf, suggestion


def enrich_schema_mappings(
    baseline_rows: list[dict[str, Any]],
    source_fields: list[dict[str, Any]],
    destination_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Upgrade baseline deterministic rows with heuristic semantic matches."""
    dest_by_name = {d["name"]: d for d in destination_fields}
    used = {r["source_field"] for r in baseline_rows if r.get("source_field")}
    out: list[dict[str, Any]] = []

    for row in baseline_rows:
        if row.get("source_field") or not row.get("target_field"):
            out.append(row)
            continue
        dest = dest_by_name.get(row["target_field"])
        if not dest:
            out.append(row)
            continue
        match = heuristic_mapping_for_target(dest, source_fields, used_sources=used)
        if not match:
            out.append(row)
            continue
        src, suggestion = match
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
                "ai_reasoning": suggestion.reasoning,
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


def suggest_lookups_heuristic(
    mapping_rows: list[dict[str, Any]],
    column_samples: dict[str, list[str]],
) -> LookupTableSuggestion:
    gaps: list[LookupGap] = []
    for row in mapping_rows:
        target = row.get("target_field")
        source = row.get("source_field")
        if not target or not source:
            continue
        constraints = row.get("target_constraints") or {}
        enum_values = constraints.get("enum") or []
        if not enum_values:
            continue
        distinct = column_samples.get(source) or row.get("sample_values") or []
        enum_upper = {str(v).upper() for v in enum_values}
        unmapped = [v for v in distinct if str(v).upper() not in enum_upper]
        if not unmapped:
            continue
        src_key = normalize_field_key(source)
        tgt_key = normalize_field_key(target)
        hint = _ENUM_LOOKUP_HINTS.get((src_key, tgt_key), {})
        proposed = {v: hint.get(v, hint.get(v.upper(), "")) for v in unmapped}
        proposed = {k: v for k, v in proposed.items() if v}
        gaps.append(
            LookupGap(
                source_field=source,
                target_field=target,
                enum_name=constraints.get("enum_name"),
                unmapped_values=unmapped,
                proposed_lookup=proposed,
                reasoning=f"{len(unmapped)} source value(s) not in {constraints.get('enum_name', target)} enum",
            )
        )
    summary = f"Found {len(gaps)} enum gap(s) requiring lookup tables"
    return LookupTableSuggestion(gaps=gaps, summary=summary)


def triage_errors_heuristic(errors: list[dict[str, Any]]) -> ErrorTriageReport:
    catalog = get_kraken_error_catalog()
    buckets: dict[str, list[dict[str, Any]]] = {}
    for err in errors:
        code = err.get("kraken_error_code") or _extract_code(err.get("error_reason", ""))
        key = code or err.get("root_cause_category") or "unknown"
        buckets.setdefault(key, []).append(err)

    clusters: list[ErrorCluster] = []
    for key, items in sorted(buckets.items(), key=lambda x: -len(x[1])):
        sample_msgs = [str(i.get("error_reason", ""))[:200] for i in items[:3]]
        detail = catalog.get(key) if key.startswith("KT-") else None
        owner = items[0].get("owner_role") or (detail or {}).get("owner_role")
        root = _infer_root_cause(key, items, detail)
        clusters.append(
            ErrorCluster(
                kraken_error_code=key if key.startswith("KT-") else None,
                error_class=key,
                count=len(items),
                sample_messages=sample_msgs,
                likely_root_cause=root,
                suggested_mapping_check=_mapping_hint(key, items),
                owner_role=owner,
            )
        )

    exec_summary = _executive_summary(clusters, len(errors))
    return ErrorTriageReport(total_errors=len(errors), clusters=clusters, executive_summary=exec_summary, provider="heuristic")


def _extract_code(text: str) -> str | None:
    import re

    m = re.search(r"KT-(CT|GB)-\d+", text.upper())
    return m.group(0) if m else None


def _infer_root_cause(code: str, items: list[dict], detail: dict | None) -> str:
    if detail and detail.get("message"):
        return detail["message"]
    if "10006" in code:
        return "Account reference not found — check number/URN padding and mapping"
    if "4036" in code:
        return "Validation failure — often postcode or address format"
    blank_number = sum(1 for i in items if not (i.get("payload") or {}).get("number"))
    if blank_number >= len(items) // 2:
        return f"{blank_number} record(s) have blank account number — check CUST_ACCOUNT_NO → number transform"
    return items[0].get("error_reason", "Review mapping and source data quality")[:300]


def _mapping_hint(code: str, items: list[dict]) -> str:
    if "10006" in code:
        return "Verify pad_left transform on account number and URN mapping"
    if "4036" in code:
        return "Check postcode and address field transforms against GB validation rules"
    if items and items[0].get("remediation_hint"):
        return items[0]["remediation_hint"]
    return "Review field mappings for affected records"


def _executive_summary(clusters: list[ErrorCluster], total: int) -> str:
    if not clusters:
        return "No errors to triage."
    top = clusters[0]
    parts = [f"{total} error(s) across {len(clusters)} cluster(s)."]
    if top.kraken_error_code:
        parts.append(f"Largest cluster: {top.count}× {top.kraken_error_code} — {top.likely_root_cause}")
    else:
        parts.append(f"Largest cluster: {top.count}× {top.error_class}")
    return " ".join(parts)


def apply_enum_lookup_transforms(
    rows: list[dict[str, Any]],
    source_fields: list[dict[str, Any]],
    destination_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Upgrade copy mappings to lookup when enum hint tables exist."""
    dest_by_name = {d["name"]: d for d in destination_fields}
    out: list[dict[str, Any]] = []
    for row in rows:
        if not row.get("source_field") or not row.get("target_field"):
            out.append(row)
            continue
        dest = dest_by_name.get(row["target_field"])
        if not dest:
            out.append(row)
            continue
        src_key = normalize_field_key(row["source_field"])
        dest_key = normalize_field_key(row["target_field"])
        lookup = _ENUM_LOOKUP_HINTS.get((src_key, dest_key))
        if not lookup:
            out.append(row)
            continue
        out.append(
            {
                **row,
                "transform_type": "lookup",
                "config": {"map": lookup, "default": ""},
                "ai_suggested": row.get("ai_suggested", True),
                "ai_reasoning": row.get("ai_reasoning")
                or f"Enum lookup for {row['source_field']} → {row['target_field']}",
                "match_confidence": row.get("match_confidence") or "high",
            }
        )
    return out
