from migration_utility.fields.catalog_parser import parse_field_catalog, suggest_field_mappings


def test_parse_source_fields_csv():
    text = """name,data_type,required,description
id,string,true,Account ID
name,string,true,Name
"""
    fields = parse_field_catalog(text, filename="source.csv")
    assert len(fields) == 2
    assert fields[0]["name"] == "id"
    assert fields[0]["required"] is True
    assert fields[1]["data_type"] == "string"


def test_parse_target_fields_json():
    text = """[
      {"name": "accountId", "data_type": "string", "required": true},
      {"name": "accountName", "data_type": "string", "required": true}
    ]"""
    fields = parse_field_catalog(text, filename="target.json")
    assert len(fields) == 2
    assert fields[0]["name"] == "accountId"


def test_suggest_mappings_by_normalized_name():
    source = [
        {"name": "id", "data_type": "string", "required": True},
        {"name": "name", "data_type": "string", "required": True},
        {"name": "status", "data_type": "string", "required": True},
    ]
    target = [
        {"name": "accountId", "data_type": "string", "required": True},
        {"name": "accountName", "data_type": "string", "required": True},
        {"name": "accountStatus", "data_type": "string", "required": True},
    ]
    suggestions = suggest_field_mappings(source, target)
    mapped = [s for s in suggestions if s.get("target_field")]
    assert len(mapped) >= 2
