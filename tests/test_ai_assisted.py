"""Tests for AI-assisted migration layer (heuristic mode in CI)."""

from migration_utility.ai.assistant import AiAssistantService
from migration_utility.ai.heuristic import apply_enum_lookup_transforms, enrich_schema_mappings, suggest_lookups_heuristic, triage_errors_heuristic
from migration_utility.ai.mapping import AiMappingService
from migration_utility.ai.provider import ai_status, provider_mode
from migration_utility.fields.catalog_parser import suggest_schema_mappings


def test_ai_status_heuristic_mode():
    status = ai_status()
    assert status["enabled"] is True
    assert status["available"] is True
    assert provider_mode() == "heuristic"


def test_ai_mapping_enriches_status_with_lookup():
    source = [
        {"name": "CUST_ACCOUNT_NO", "data_type": "string"},
        {"name": "ACCT_STATUS_CODE", "data_type": "string", "sample_values": ["A", "P"]},
    ]
    dest = [
        {"name": "number", "data_type": "string", "required": True},
        {"name": "status", "data_type": "enum", "required": True, "constraints": {
            "enum": ["ACTIVE", "PENDING", "WITHDRAWN", "DORMANT"],
            "enum_name": "AccountStatus",
        }},
    ]
    baseline = suggest_schema_mappings(source, dest)
    rows = apply_enum_lookup_transforms(
        enrich_schema_mappings(baseline, source, dest), source, dest
    )
    status_row = next(r for r in rows if r["target_field"] == "status")
    assert status_row["source_field"] == "ACCT_STATUS_CODE"
    assert status_row["transform_type"] == "lookup"
    assert status_row["ai_suggested"] is True
    assert status_row["config"]["map"]["A"] == "ACTIVE"


def test_ai_mapping_service_end_to_end():
    source = [
        {"name": "CUST_TYPE_FLAG", "data_type": "string", "sample_values": ["O"]},
    ]
    dest = [
        {"name": "accountType", "data_type": "enum", "required": True, "constraints": {
            "enum": ["DOMESTIC", "OCCUPIER", "BUSINESS"],
            "enum_name": "AccountTypeChoices",
        }},
    ]
    rows = AiMappingService().suggest_schema_mappings(source, dest)
    row = rows[0]
    assert row["source_field"] == "CUST_TYPE_FLAG"
    assert row["transform_type"] == "lookup"
    assert row["config"]["map"]["O"] == "OCCUPIER"


def test_lookup_gap_detection():
    rows = [
        {
            "source_field": "CUST_TYPE_FLAG",
            "target_field": "accountType",
            "target_constraints": {"enum": ["DOMESTIC", "OCCUPIER"], "enum_name": "AccountTypeChoices"},
        }
    ]
    samples = {"CUST_TYPE_FLAG": ["O", "X"]}
    result = suggest_lookups_heuristic(rows, samples)
    assert len(result.gaps) == 1
    assert "X" in result.gaps[0].unmapped_values
    assert result.gaps[0].proposed_lookup.get("O") == "OCCUPIER"


def test_error_triage_clusters():
    errors = [
        {"kraken_error_code": "KT-CT-10006", "error_reason": "Account not found", "payload": {}},
        {"kraken_error_code": "KT-CT-10006", "error_reason": "Account not found", "payload": {"number": ""}},
        {"kraken_error_code": "KT-GB-4036", "error_reason": "Postcode invalid", "payload": {}},
    ]
    report = triage_errors_heuristic(errors)
    assert report.total_errors == 3
    assert len(report.clusters) == 2
    assert report.executive_summary


def test_assistant_kraken_code_question():
    reply = AiAssistantService().answer("What does KT-CT-10006 mean?")
    assert "10006" in reply.answer or "account" in reply.answer.lower()
    assert reply.references
