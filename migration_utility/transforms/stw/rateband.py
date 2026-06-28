"""STW rate band → Kraken tariff lookup rules."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from migration_utility.transforms.stw.property_type import _first, _is_metered, _normalize_category


def _start_year(record: dict[str, Any], field: str) -> str | None:
    raw = record.get(field)
    if not raw:
        return None
    text = str(raw).strip()
    if len(text) >= 4 and text[:4].isdigit():
        return text[:4]
    try:
        return str(datetime.fromisoformat(text.replace("Z", "+00:00")).year)
    except ValueError:
        return None


def _row_key(record: dict[str, Any], rules: dict[str, Any], keys: list[str]) -> dict[str, str]:
    key_map = {
        "product_code": rules.get("product_code_field", "target_product_code"),
        "rate_band": rules.get("rate_band_field", "target_rate_band"),
        "area_code": rules.get("area_code_field", "area_code"),
        "property_type": rules.get("property_type_field", "property_type"),
        "start_year": rules.get("start_date_field", "kraken_start_date"),
        "kraken_product_code": rules.get("kraken_product_code_field", "kraken_product_code"),
    }
    out: dict[str, str] = {}
    for k in keys:
        field = key_map.get(k, k)
        if k == "start_year":
            val = _start_year(record, field)
        else:
            val = record.get(field)
        if val is not None and str(val).strip() != "":
            out[k] = str(val).strip()
    return out


def _is_drainage_product(code: str, prefixes: list[str]) -> bool:
    upper = code.upper()
    return any(upper.startswith(p.upper()) for p in prefixes)


def _match_profile(record: dict[str, Any], rules: dict[str, Any], profile: dict[str, Any]) -> bool:
    category = _normalize_category(
        _first(record, [rules.get("category_field", "account_category"), "category"]),
        {},
    )
    product = str(_first(record, [rules.get("product_code_field", "target_product_code")]) or "")
    metered = _is_metered(record, rules)
    drainage_prefixes = rules.get("drainage_product_prefixes", [])
    is_drainage = _is_drainage_product(product, drainage_prefixes)

    if profile.get("drainage_only") and not is_drainage:
        return False
    if profile.get("exclude_drainage") and is_drainage:
        return False
    if "categories" in profile and category not in profile["categories"]:
        return False
    if "metered" in profile and profile["metered"] != metered:
        return False
    if "product_prefixes" in profile:
        if not any(product.upper().startswith(p.upper()) for p in profile["product_prefixes"]):
            return False
    return True


def _lookup_rows(table: list[dict], key: dict[str, str]) -> list[dict]:
    matches = []
    for row in table:
        if all(str(row.get(k, "")).strip() == v for k, v in key.items()):
            matches.append(row)
    return matches


def transform_rateband(
    record: dict[str, Any],
    rules: dict[str, Any],
) -> dict[str, Any] | None:
    """Return matched tariff row (kraken product + rate metadata) or None."""
    table = rules.get("tariff_table") or []
    if not table:
        return None

    for profile in rules.get("lookup_profiles", []):
        if not _match_profile(record, rules, profile):
            continue
        keys = profile.get("keys", [])
        matches = _lookup_rows(table, _row_key(record, rules, keys))
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1 and profile.get("fallback_keys"):
            narrowed = _lookup_rows(
                matches,
                _row_key(record, rules, profile["fallback_keys"]),
            )
            if len(narrowed) == 1:
                return narrowed[0]
            if len(narrowed) > 1:
                return narrowed[0]
        if matches:
            return matches[0]
    return None
