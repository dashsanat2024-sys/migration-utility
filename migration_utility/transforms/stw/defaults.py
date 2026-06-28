"""Default STW → Kraken transformation rules (editable per project via API)."""

from __future__ import annotations

from typing import Any

# --- Property type (from property_type_transformation_rule.jpeg) ---

DEFAULT_PROPERTY_TYPE_RULES: dict[str, Any] = {
    "category_field": "account_category",
    "property_type_field": "property_type",
    "supply_address_fields": ["supply_address", "address", "supplyAddress", "ADDR_LINE"],
    "meter_tag_fields": ["meter_tag", "meterTag", "has_meter"],
    "meter_ignore_field": "should_be_ignored",
    "product_code_fields": ["product_code", "target_product_code", "MDD_CODE"],
    "value_map": {
        "Terraced": "TERRACED",
        "Semi Detached": "SEMI_DETACHED",
        "Detached": "DETACHED",
        "Not Known": "DETACHED",
    },
    "not_known_applies_to": ["stw_measured", "assessed"],
    "mdd_product_map": {
        "MDD01": "DETACHED",
        "MDD02": "SEMI_DETACHED",
        "MDD03": "TERRACED",
        "MDD04": "FLAT",
    },
    "mdd_rule_metered_categories": ["stw_measured", "bds", "watersure"],
    "mdd_rule_unmeasured_categories": ["assessed"],
    "flat_address_keywords": ["flat", "apartment", "apartments", "studio"],
    "flat_rule_categories": ["stw_unmeasured", "bds", "watersure"],
    "category_aliases": {
        "STW Measured": "stw_measured",
        "STW Unmeasured": "stw_unmeasured",
        "Assessed": "assessed",
        "OWC": "owc",
        "BDS": "bds",
        "Watersure": "watersure",
    },
}

# --- Area code (from area_code_transformation_rule.jpeg) ---

DEFAULT_AREA_CODE_RULES: dict[str, Any] = {
    "area_code_field": "area_code",
    "fresh_area_code_field": "fresh_area_code",
    "waste_area_code_field": "waste_area_code",
    "category_field": "account_category",
    "product_code_fields": ["product_code", "target_product_code"],
    "zone_map": {
        "Zone 01 - STW Shropshire (Upper Severn)": "ZONE_1",
        "Zone 02 - STW Worcester/Gloucester (Lower Severn)": "ZONE_2",
        "Zone 03 - STW Coventry/North Warks (Avon)": "ZONE_3",
        "Zone 04 - STW Leicestershire (Soar)": "ZONE_4",
        "Zone 05 - STW Nottinghamshire (Lower Trent)": "ZONE_5",
        "Zone 06 - STW Derbyshire (Derwent)": "ZONE_6",
        "Zone 07 - STW Staffordshire (Upper Trent)": "ZONE_7",
        "Zone 08 - STW Birmingham (Tame)": "ZONE_8",
        "Zone 23 - STW Chester": "ZONE_8",
        "Zone 11 - North West Water": "ZONE_11",
        "Zone 14 - Thames Water": "ZONE_14",
        "Zone 10 - Yorkshire Water": "ZONE_10",
        "Zone 24 - STW Wrexham": "ZONE_10",
        "Zone 12 - Welsh Water": "ZONE_12",
    },
    "default_zone": "ZONE_1",
    "assessed_product_prefixes": ["ASB", "AVB", "MDD"],
    "assessed_suffix_zone_map": {
        "24": "ZONE_9",
        "21": "ZONE_9",
        "34": "ZONE_10",
    },
    "assessed_mdd_priority": True,
    "account_blank_rules": {
        "bds": {"default_zone": "ZONE_1"},
        "owc": {"use_tariff_mapping": True},
        "stw_measured": {"use_tariff_mapping": True},
        "watersure": {"use_tariff_mapping": True},
    },
    "propagate_area_code_except_owc": True,
    "category_aliases": DEFAULT_PROPERTY_TYPE_RULES["category_aliases"],
    "tariff_area_code_field": "area_code",
}

# --- Rate band / tariff lookup (from rateband_transformation_rule.jpeg) ---

DEFAULT_RATEBAND_RULES: dict[str, Any] = {
    "product_code_field": "target_product_code",
    "rate_band_field": "target_rate_band",
    "area_code_field": "area_code",
    "property_type_field": "property_type",
    "start_date_field": "kraken_start_date",
    "kraken_product_code_field": "kraken_product_code",
    "category_field": "account_category",
    "metered_field": "metered",
    "drainage_product_prefixes": ["ISTV-HA", "ISTV-HS", "ISTV-MOD"],
    "lookup_profiles": [
        {
            "id": "watersure_measured",
            "categories": ["watersure"],
            "metered": True,
            "exclude_drainage": True,
            "keys": ["product_code", "rate_band", "start_year"],
            "fallback_keys": ["property_type"],
        },
        {
            "id": "bds_measured",
            "categories": ["bds"],
            "metered": True,
            "exclude_drainage": True,
            "keys": ["product_code", "rate_band", "start_year"],
        },
        {
            "id": "bds_unmeasured",
            "categories": ["bds"],
            "metered": False,
            "exclude_drainage": True,
            "keys": ["product_code", "rate_band", "start_year"],
        },
        {
            "id": "owc_measured",
            "categories": ["owc"],
            "metered": True,
            "exclude_drainage": True,
            "keys": ["product_code", "rate_band", "start_year"],
            "fallback_keys": ["property_type"],
        },
        {
            "id": "owc_unmeasured",
            "categories": ["owc"],
            "metered": False,
            "exclude_drainage": True,
            "keys": ["product_code", "rate_band", "start_year"],
        },
        {
            "id": "assessed_unmeasured_fresh",
            "categories": ["assessed"],
            "metered": False,
            "product_prefixes": ["AVE"],
            "exclude_drainage": True,
            "keys": ["product_code", "rate_band", "area_code", "start_year"],
            "fallback_keys": ["property_type"],
        },
        {
            "id": "waste_ase",
            "product_prefixes": ["ASE"],
            "exclude_drainage": True,
            "keys": ["product_code", "rate_band", "start_year"],
            "fallback_keys": ["property_type"],
        },
        {
            "id": "stw_unmeasured",
            "categories": ["stw_unmeasured"],
            "metered": False,
            "exclude_drainage": True,
            "keys": ["product_code", "rate_band", "area_code", "start_year"],
        },
        {
            "id": "stw_measured",
            "categories": ["stw_measured"],
            "metered": True,
            "exclude_drainage": True,
            "keys": ["product_code", "rate_band", "start_year"],
            "fallback_keys": ["property_type"],
        },
        {
            "id": "drainage_assessed_unmeasured",
            "drainage_only": True,
            "metered": False,
            "categories": ["assessed"],
            "keys": ["product_code", "rate_band", "start_year", "kraken_product_code"],
            "fallback_keys": ["property_type"],
        },
        {
            "id": "drainage_unmeasured",
            "drainage_only": True,
            "metered": False,
            "keys": ["product_code", "rate_band", "area_code", "start_year", "kraken_product_code"],
            "fallback_keys": ["property_type"],
        },
    ],
    "tariff_table": [],
}

DEFAULT_STW_TRANSFORM_RULES: dict[str, Any] = {
    "property_type": DEFAULT_PROPERTY_TYPE_RULES,
    "area_code": DEFAULT_AREA_CODE_RULES,
    "rateband": DEFAULT_RATEBAND_RULES,
}
