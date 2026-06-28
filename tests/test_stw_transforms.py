"""Tests for STW → Kraken transformation rules."""

from migration_utility.rules.engine import TransformEngine
from migration_utility.rules.types import FieldMappingDef
from migration_utility.transforms.stw import (
    get_stw_rules,
    transform_area_code,
    transform_property_type,
    transform_rateband,
)


def test_property_type_standard_mapping():
    rules = get_stw_rules({})["property_type"]
    record = {"account_category": "STW Measured", "property_type": "Semi Detached", "meter_tag": "M1"}
    assert transform_property_type(record, rules) == "SEMI_DETACHED"


def test_property_type_mdd_override():
    rules = get_stw_rules({})["property_type"]
    record = {
        "account_category": "Assessed",
        "property_type": "Detached",
        "product_code": "MDD02",
    }
    assert transform_property_type(record, rules) == "SEMI_DETACHED"


def test_property_type_flat_from_address():
    rules = get_stw_rules({})["property_type"]
    record = {
        "account_category": "BDS",
        "property_type": "Detached",
        "supply_address": "Flat 2, High Street",
    }
    assert transform_property_type(record, rules) == "FLAT"


def test_property_type_not_known_assessed_only():
    rules = get_stw_rules({})["property_type"]
    assessed = {"account_category": "Assessed", "property_type": "Not Known"}
    bds = {"account_category": "BDS", "property_type": "Not Known", "supply_address": "1 Main St"}
    assert transform_property_type(assessed, rules) == "DETACHED"
    assert transform_property_type(bds, rules) is None


def test_area_code_zone_map():
    rules = get_stw_rules({})["area_code"]
    record = {"account_category": "STW Measured", "area_code": "Zone 23 - STW Chester"}
    assert transform_area_code(record, rules) == "ZONE_8"


def test_area_code_assessed_suffix():
    rules = get_stw_rules({})["area_code"]
    record = {"account_category": "Assessed", "product_code": "ASB24"}
    assert transform_area_code(record, rules) == "ZONE_9"


def test_area_code_blank_bds_default():
    rules = get_stw_rules({})["area_code"]
    record = {"account_category": "BDS", "area_code": ""}
    assert transform_area_code(record, rules) == "ZONE_1"


def test_area_code_tariff_fallback():
    rules = get_stw_rules({})["area_code"]
    record = {"account_category": "STW Measured", "area_code": "", "product_code": "PROD-A"}
    context = {"tariff_table": [{"product_code": "PROD-A", "area_code": "ZONE_3"}]}
    assert transform_area_code(record, rules, context=context) == "ZONE_3"


def test_rateband_lookup_single_match():
    rules = get_stw_rules({})["rateband"]
    rules["tariff_table"] = [
        {
            "product_code": "WTR-01",
            "rate_band": "RB1",
            "start_year": "2024",
            "kraken_rate_band": "KRB1",
            "kraken_product_code": "KPROD1",
        }
    ]
    record = {
        "account_category": "stw_measured",
        "metered": True,
        "target_product_code": "WTR-01",
        "target_rate_band": "RB1",
        "kraken_start_date": "2024-06-01",
    }
    row = transform_rateband(record, rules)
    assert row is not None
    assert row["kraken_rate_band"] == "KRB1"


def test_rateband_lookup_property_type_fallback():
    rules = get_stw_rules({})["rateband"]
    rules["tariff_table"] = [
        {
            "product_code": "WTR-01",
            "rate_band": "RB1",
            "start_year": "2024",
            "property_type": "DETACHED",
            "kraken_rate_band": "KRB-D",
        },
        {
            "product_code": "WTR-01",
            "rate_band": "RB1",
            "start_year": "2024",
            "property_type": "FLAT",
            "kraken_rate_band": "KRB-F",
        },
    ]
    record = {
        "account_category": "watersure",
        "metered": True,
        "target_product_code": "WTR-01",
        "target_rate_band": "RB1",
        "kraken_start_date": "2024-01-01",
        "property_type": "FLAT",
    }
    row = transform_rateband(record, rules)
    assert row["kraken_rate_band"] == "KRB-F"


def test_transform_engine_stw_property_type():
    engine = TransformEngine()
    stw = get_stw_rules({})
    mappings = [
        FieldMappingDef(
            "1",
            "property_type",
            "kraken_property_type",
            "stw_property_type",
            {},
            True,
            1,
        ),
    ]
    records = [{"account_category": "STW Measured", "property_type": "Terraced", "meter_tag": "x"}]
    out = engine.apply(records, mappings, context={"stw_transform_rules": stw})
    assert out[0]["kraken_property_type"] == "TERRACED"


def test_project_override_merges():
    cfg = {"stw_transform_rules": {"property_type": {"value_map": {"Terraced": "TERRACED_CUSTOM"}}}}
    rules = get_stw_rules(cfg)["property_type"]
    assert rules["value_map"]["Terraced"] == "TERRACED_CUSTOM"
    assert rules["value_map"]["Detached"] == "DETACHED"
