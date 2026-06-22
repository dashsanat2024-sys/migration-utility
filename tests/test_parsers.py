import pytest

from migration_utility.ingest.parsers import parse_csv, parse_json, parse_xml


def test_parse_csv():
    text = "id,name,status\nACC-001,Alice,active\nACC-002,Bob,inactive\n"
    rows = parse_csv(text)
    assert len(rows) == 2
    assert rows[0]["id"] == "ACC-001"


def test_parse_json_array():
    text = '[{"id": "1", "name": "A", "status": "active"}]'
    rows = parse_json(text)
    assert len(rows) == 1
    assert rows[0]["name"] == "A"


def test_parse_json_wrapper():
    text = '{"records": [{"id": "1", "name": "A", "status": "active"}]}'
    rows = parse_json(text)
    assert len(rows) == 1


def test_parse_xml():
    text = """
    <accounts>
      <record id="ACC-001">
        <name>Alice</name>
        <status>active</status>
      </record>
    </accounts>
    """
    rows = parse_xml(text)
    assert len(rows) == 1
    assert rows[0]["name"] == "Alice"
    assert rows[0]["id"] == "ACC-001"
