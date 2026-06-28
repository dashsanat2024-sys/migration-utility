"""STW property type transformation (metered / unmeasured rules)."""

from __future__ import annotations

import re
from typing import Any


def _first(record: dict[str, Any], fields: list[str]) -> Any:
    for f in fields:
        if f in record and record[f] not in (None, ""):
            return record[f]
    return None


def _normalize_category(raw: Any, aliases: dict[str, str]) -> str:
    if raw is None:
        return ""
    text = str(raw).strip()
    if text in aliases:
        return aliases[text]
    return text.lower().replace(" ", "_")


def _is_metered(record: dict[str, Any], rules: dict[str, Any]) -> bool:
    explicit = record.get(rules.get("metered_field", "metered"))
    if explicit is not None:
        return str(explicit).lower() in ("true", "1", "yes", "y", "metered")
    meter_tag = _first(record, rules.get("meter_tag_fields", []))
    if meter_tag is None:
        return False
    ignore = record.get(rules.get("meter_ignore_field", "should_be_ignored"))
    if str(ignore).lower() in ("true", "1", "yes"):
        return False
    return bool(str(meter_tag).strip())


def _address_text(record: dict[str, Any], rules: dict[str, Any]) -> str:
    parts = []
    for f in rules.get("supply_address_fields", []):
        val = record.get(f)
        if val:
            parts.append(str(val))
    return " ".join(parts).lower()


def _flat_from_address(record: dict[str, Any], rules: dict[str, Any]) -> bool:
    text = _address_text(record, rules)
    if not text:
        return False
    for kw in rules.get("flat_address_keywords", []):
        if re.search(rf"\b{re.escape(kw.lower())}\b", text):
            return True
    return False


def _mdd_product_code(record: dict[str, Any], rules: dict[str, Any]) -> str | None:
    code = _first(record, rules.get("product_code_fields", []))
    if not code:
        return None
    text = str(code).upper()
    for prefix in ("MDD", "ASB", "AVB"):
        if text.startswith(prefix):
            return text[:5] if len(text) >= 5 else text
    m = re.search(r"(MDD\d{2})", text)
    return m.group(1) if m else None


def transform_property_type(record: dict[str, Any], rules: dict[str, Any]) -> str | None:
    category = _normalize_category(
        _first(record, [rules.get("category_field", "account_category"), "category"]),
        rules.get("category_aliases", {}),
    )
    metered = _is_metered(record, rules)
    flat_categories = set(rules.get("flat_rule_categories", []))

    if category in flat_categories and _flat_from_address(record, rules):
        return "FLAT"

    mdd_metered = set(rules.get("mdd_rule_metered_categories", []))
    mdd_unmeasured = set(rules.get("mdd_rule_unmeasured_categories", []))
    use_mdd = (metered and category in mdd_metered) or (not metered and category in mdd_unmeasured)
    if use_mdd:
        mdd = _mdd_product_code(record, rules)
        if mdd and mdd in rules.get("mdd_product_map", {}):
            return rules["mdd_product_map"][mdd]

    raw = _first(record, [rules.get("property_type_field", "property_type"), "propertyType"])
    if raw is None:
        return None
    text = str(raw).strip()
    mapped = rules.get("value_map", {}).get(text)
    if text == "Not Known":
        if category in rules.get("not_known_applies_to", []):
            return mapped or "DETACHED"
        return None
    return mapped or text.upper().replace(" ", "_")
