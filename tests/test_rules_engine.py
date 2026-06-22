from migration_utility.rules.engine import TransformEngine, ValidationEngine
from migration_utility.rules.types import FieldMappingDef, ValidationRuleDef


def test_validation_format_and_in_list():
    engine = ValidationEngine()
    rules = [
        ValidationRuleDef("1", "id fmt", "format", "id", {"pattern": r"^ACC-\d+$"}),
        ValidationRuleDef("2", "status", "in_list", "status", {"values": ["active", "inactive"]}),
    ]
    records = [
        {"id": "ACC-001", "name": "A", "status": "active"},
        {"id": "BAD", "name": "B", "status": "active"},
        {"id": "ACC-003", "name": "C", "status": "unknown"},
    ]
    valid, invalid, reasons = engine.apply(records, rules)
    assert len(valid) == 1
    assert len(invalid) == 2
    assert len(reasons) == 2


def test_validation_unique():
    engine = ValidationEngine()
    rules = [ValidationRuleDef("1", "uniq", "unique", "id", {})]
    records = [
        {"id": "ACC-001", "name": "A"},
        {"id": "ACC-001", "name": "B"},
    ]
    valid, invalid, _ = engine.apply(records, rules)
    assert len(valid) == 1
    assert len(invalid) == 1


def test_transform_lookup_and_copy():
    engine = TransformEngine()
    mappings = [
        FieldMappingDef("1", "id", "accountId", "copy", {}, True, 1),
        FieldMappingDef("2", "status", "accountStatus", "lookup", {"map": {"active": "ACTIVE"}}, True, 2),
    ]
    records = [{"id": "ACC-001", "name": "Alice", "status": "active"}]
    out = engine.apply(records, mappings)
    assert out[0]["accountId"] == "ACC-001"
    assert out[0]["accountStatus"] == "ACTIVE"


def test_transform_concat():
    engine = TransformEngine()
    mappings = [
        FieldMappingDef(
            "1", None, "fullName", "concat", {"fields": ["first", "last"], "separator": " "}, True, 1
        ),
    ]
    records = [{"first": "John", "last": "Doe"}]
    out = engine.apply(records, mappings)
    assert out[0]["fullName"] == "John Doe"


def test_transform_pad_left_and_regex_replace():
    engine = TransformEngine()
    mappings = [
        FieldMappingDef("1", "NO_ACCOUNT", "account_number", "pad_left", {"width": 9, "char": "0"}, True, 1),
        FieldMappingDef(
            "2",
            "NM_TIT_IND_134",
            "customer_title",
            "uppercase",
            {},
            True,
            2,
        ),
        FieldMappingDef(
            "3",
            "rateband",
            "rateband_clean",
            "regex_replace",
            {"pattern": " AdVAT", "replacement": ""},
            True,
            3,
        ),
    ]
    records = [{"NO_ACCOUNT": "1234567", "NM_TIT_IND_134": "mr", "rateband": "Meas Water Cons AdVAT HHW"}]
    out = engine.apply(records, mappings)
    assert out[0]["account_number"] == "001234567"
    assert out[0]["customer_title"] == "MR"
    assert out[0]["rateband_clean"] == "Meas Water Cons HHW"
