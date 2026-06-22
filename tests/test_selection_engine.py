from migration_utility.selection.engine import SelectionEngine
from migration_utility.selection.service import _dedupe_by_external_id
from migration_utility.selection.types import CriterionDef, SelectionLogic, SelectionOperator


def test_selection_dedupe_duplicate_staging_rows():
    rows = [
        {"_row_id": "a", "_row_number": 1, "id": "ACC-001", "status": "active"},
        {"_row_id": "b", "_row_number": 2, "id": "ACC-001", "status": "active"},
        {"_row_id": "c", "_row_number": 3, "id": "ACC-002", "status": "active"},
    ]
    deduped = _dedupe_by_external_id(rows)
    assert len(deduped) == 2
    assert deduped[0]["_row_id"] == "a"


def test_selection_eq_and_in():
    engine = SelectionEngine()
    records = [
        {"id": "1", "status": "active", "region": "north"},
        {"id": "2", "status": "inactive", "region": "south"},
        {"id": "3", "status": "active", "region": "east"},
    ]
    criteria = [
        CriterionDef(None, "status", SelectionOperator.EQ.value, "active"),
    ]
    selected, excluded = engine.apply(records, criteria, logic=SelectionLogic.AND.value)
    assert len(selected) == 2
    assert len(excluded) == 1
    assert excluded[0]["id"] == "2"


def test_selection_or_logic():
    engine = SelectionEngine()
    records = [
        {"id": "1", "status": "active"},
        {"id": "2", "status": "pending"},
        {"id": "3", "status": "closed"},
    ]
    criteria = [
        CriterionDef(None, "status", SelectionOperator.EQ.value, "active", sort_order=1),
        CriterionDef(None, "status", SelectionOperator.EQ.value, "pending", sort_order=2),
    ]
    selected, _ = engine.apply(records, criteria, logic=SelectionLogic.OR.value)
    assert len(selected) == 2


def test_selection_limit():
    engine = SelectionEngine()
    records = [{"id": str(i), "status": "active"} for i in range(10)]
    criteria = [CriterionDef(None, "status", SelectionOperator.EQ.value, "active")]
    selected, _ = engine.apply(records, criteria, limit=3)
    assert len(selected) == 3


def test_selection_disabled_criterion_ignored():
    engine = SelectionEngine()
    records = [
        {"id": "1", "status": "active"},
        {"id": "2", "status": "inactive"},
    ]
    criteria = [
        CriterionDef(None, "status", SelectionOperator.EQ.value, "active", enabled=False),
    ]
    selected, _ = engine.apply(records, criteria)
    assert len(selected) == 2
