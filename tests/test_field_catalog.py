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


def test_parse_data_extract_csv_uses_column_headers():
    """Tabular extract (Target/CMP) — columns become source fields, not cell values."""
    text = """CUST_ACCOUNT_NO,CUST_TYPE_FLAG,CUST_FNAME,STEPPED_RATE_FLAG,COMPLAINT_FLAG
410583920,D,James,Y,N
410612847,D,Sarah,N,N
"""
    fields = parse_field_catalog(text, filename="target_cmp_sample_extract.csv")
    names = [f["name"] for f in fields]
    assert names == [
        "CUST_ACCOUNT_NO",
        "CUST_TYPE_FLAG",
        "CUST_FNAME",
        "STEPPED_RATE_FLAG",
        "COMPLAINT_FLAG",
    ]
    assert fields[0]["data_type"] == "string"
    assert fields[3]["data_type"] == "bool"
    assert fields[4]["data_type"] == "bool"
    assert "410583920" not in names


def test_suggest_schema_mappings_cmp_to_kraken_aliases():
    from migration_utility.fields.catalog_parser import suggest_schema_mappings

    source = parse_field_catalog(
        """CUST_ACCOUNT_NO,CUST_TYPE_FLAG,LEGACY_SYS_REF,STEPPED_RATE_FLAG
410583920,D,CMP-001,Y
""",
        filename="target_cmp_sample_extract.csv",
    )
    dest = [
        {"name": "number", "required": True},
        {"name": "accountType", "required": True},
        {"name": "urn"},
        {"name": "isOnSteppedTariff", "required": True},
    ]
    rows = suggest_schema_mappings(source, dest)
    by_target = {r["target_field"]: r.get("source_field") for r in rows if r.get("target_field")}
    assert by_target.get("number") == "CUST_ACCOUNT_NO"
    assert by_target.get("urn") == "LEGACY_SYS_REF"
    assert by_target.get("isOnSteppedTariff") == "STEPPED_RATE_FLAG"
    assert by_target.get("accountType") == "CUST_TYPE_FLAG"

