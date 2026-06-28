"""STW area code transformation rules."""

from __future__ import annotations

import re
from typing import Any

from migration_utility.transforms.stw.property_type import _first, _normalize_category


def _map_zone(raw: Any, zone_map: dict[str, str]) -> str | None:
    if raw is None or str(raw).strip() == "":
        return None
    text = str(raw).strip()
    if text in zone_map:
        return zone_map[text]
    upper = text.upper()
    if upper.startswith("ZONE_"):
        return upper
    m = re.search(r"ZONE[_\s-]?(\d+)", upper)
    if m:
        return f"ZONE_{int(m.group(1))}"
    return zone_map.get(text)


def _assessed_zone_from_products(record: dict[str, Any], rules: dict[str, Any]) -> str | None:
    codes = []
    for f in rules.get("product_code_fields", []):
        val = record.get(f)
        if val:
            codes.append(str(val).upper())
    if not codes:
        single = record.get("product_code")
        if single:
            codes = [str(single).upper()]

    prefixes = rules.get("assessed_product_prefixes", ["ASB", "AVB", "MDD"])
    suffix_map = rules.get("assessed_suffix_zone_map", {})
    mdd_codes = [c for c in codes if c.startswith("MDD")]
    if rules.get("assessed_mdd_priority") and mdd_codes:
        codes = mdd_codes + [c for c in codes if not c.startswith("MDD")]

    for code in codes:
        if not any(code.startswith(p) for p in prefixes):
            continue
        suffix = code[-2:] if len(code) >= 2 else ""
        if suffix in suffix_map:
            return suffix_map[suffix]
    return None


def _tariff_zone(record: dict[str, Any], rules: dict[str, Any], context: dict[str, Any]) -> str | None:
    table = context.get("tariff_table") or rules.get("tariff_table") or []
    product = _first(record, rules.get("product_code_fields", ["target_product_code"]))
    if not product:
        return None
    for row in table:
        if str(row.get("product_code", "")).upper() == str(product).upper():
            zone = row.get("area_code") or row.get("zone")
            if zone:
                return str(zone)
    mappings = context.get("tariff_mappings") or {}
    return mappings.get(str(product))


def transform_area_code(
    record: dict[str, Any],
    rules: dict[str, Any],
    *,
    context: dict[str, Any] | None = None,
) -> str | None:
    ctx = context or {}
    category = _normalize_category(
        _first(record, [rules.get("category_field", "account_category"), "category"]),
        rules.get("category_aliases", {}),
    )
    zone_map = rules.get("zone_map", {})
    default = rules.get("default_zone", "ZONE_1")

    fresh = _first(record, [rules.get("fresh_area_code_field", "fresh_area_code")])
    waste = _first(record, [rules.get("waste_area_code_field", "waste_area_code")])
    primary = _first(record, [rules.get("area_code_field", "area_code")])

    if category == "assessed":
        assessed = _assessed_zone_from_products(record, rules)
        if assessed:
            return assessed

    resolved = _map_zone(primary, zone_map) or _map_zone(fresh, zone_map) or _map_zone(waste, zone_map)

    if not resolved and category in rules.get("account_blank_rules", {}):
        blank_rule = rules["account_blank_rules"][category]
        if blank_rule.get("default_zone"):
            resolved = blank_rule["default_zone"]
        elif blank_rule.get("use_tariff_mapping"):
            resolved = _tariff_zone(record, rules, ctx)

    if not resolved:
        resolved = default

    if rules.get("propagate_area_code_except_owc") and category != "owc":
        if fresh and not waste:
            record[rules.get("waste_area_code_field", "waste_area_code")] = resolved
        elif waste and not fresh:
            record[rules.get("fresh_area_code_field", "fresh_area_code")] = resolved

    return resolved
