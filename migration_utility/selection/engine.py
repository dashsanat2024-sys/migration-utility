from __future__ import annotations

from typing import Any

from migration_utility.selection.types import CriterionDef, SelectionLogic, SelectionOperator


class SelectionEngine:
    """Filter records using switchable selection criteria."""

    def apply(
        self,
        records: list[dict[str, Any]],
        criteria: list[CriterionDef],
        *,
        logic: str = SelectionLogic.AND.value,
        limit: int | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        active = [c for c in criteria if c.enabled]
        if not active:
            selected = list(records)
        elif logic == SelectionLogic.OR.value:
            selected = [r for r in records if any(self._matches(r, c) for c in active)]
        else:
            selected = [r for r in records if all(self._matches(r, c) for c in active)]

        if limit is not None and limit >= 0:
            selected = selected[:limit]

        selected_ids = {id(r) for r in selected}
        excluded = [r for r in records if id(r) not in selected_ids]
        return selected, excluded

    def _matches(self, record: dict[str, Any], criterion: CriterionDef) -> bool:
        op = criterion.operator
        raw = record.get(criterion.field_name)
        value = criterion.value

        if op == SelectionOperator.IS_NULL.value:
            return raw is None or raw == ""
        if op == SelectionOperator.IS_NOT_NULL.value:
            return raw is not None and raw != ""
        if op == SelectionOperator.EQ.value:
            return _normalize(raw) == _normalize(value)
        if op == SelectionOperator.NE.value:
            return _normalize(raw) != _normalize(value)
        if op == SelectionOperator.IN.value:
            options = value if isinstance(value, list) else [value]
            return _normalize(raw) in {_normalize(v) for v in options}
        if op == SelectionOperator.NOT_IN.value:
            options = value if isinstance(value, list) else [value]
            return _normalize(raw) not in {_normalize(v) for v in options}
        if op == SelectionOperator.CONTAINS.value:
            return str(value).lower() in str(raw or "").lower()
        if op == SelectionOperator.STARTS_WITH.value:
            return str(raw or "").lower().startswith(str(value).lower())
        if op in (
            SelectionOperator.GT.value,
            SelectionOperator.GTE.value,
            SelectionOperator.LT.value,
            SelectionOperator.LTE.value,
        ):
            return _compare(raw, value, op)
        return False


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _compare(left: Any, right: Any, op: str) -> bool:
    try:
        lnum = float(left)
        rnum = float(right)
    except (TypeError, ValueError):
        lnum = str(left or "")
        rnum = str(right or "")
    if op == SelectionOperator.GT.value:
        return lnum > rnum
    if op == SelectionOperator.GTE.value:
        return lnum >= rnum
    if op == SelectionOperator.LT.value:
        return lnum < rnum
    if op == SelectionOperator.LTE.value:
        return lnum <= rnum
    return False
