"""Queryable Kraken error catalog (~920 codes indexed, 57 with confirmed message text)."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

from migration_utility.kraken.errors.detailed import DETAILED_ENTRIES, KrakenErrorDetail
from migration_utility.kraken.errors.ranges import ALL_RANGES, CATEGORY_LABELS, CodeRange

_CODE_RE = re.compile(r"KT-(CT|GB)-(\d+)")
# Sourced index total from developer.pwl.kraken.tech (~700 KT-CT + ~220 KT-GB)
DOCUMENTED_TOTAL_CODES = 920


def _code_str(prefix: str, num: int) -> str:
    return f"{prefix}-{num}"


def _parse_code(code: str) -> tuple[str, int] | None:
    match = _CODE_RE.match(code.strip().upper())
    if not match:
        return None
    return f"KT-{match.group(1)}", int(match.group(2))


def _range_for_number(prefix: str, num: int) -> CodeRange | None:
    for r in ALL_RANGES:
        if r["prefix"] == prefix and r["start"] <= num <= r["end"]:
            return r
    return None


def _index_entry(prefix: str, num: int, detail: KrakenErrorDetail | None) -> dict[str, Any]:
    code = _code_str(prefix, num)
    if detail:
        return {
            **detail,
            "has_detail": True,
            "indexed_only": False,
        }
    rng = _range_for_number(prefix, num)
    if not rng:
        return {
            "code": code,
            "error_type": "UNKNOWN",
            "trigger": "",
            "message": "",
            "category": "unknown",
            "migration_phase": "at_load",
            "migration_relevance": "low",
            "owner_role": "migration_engineer",
            "is_blocker": False,
            "has_detail": False,
            "indexed_only": True,
        }
    return {
        "code": code,
        "error_type": "INDEXED",
        "trigger": rng["label"],
        "message": "",
        "category": rng["category"],
        "migration_phase": rng["default_phase"],
        "migration_relevance": rng["migration_relevance"],
        "owner_role": rng["default_owner"],
        "is_blocker": rng["migration_relevance"] in ("high", "medium"),
        "has_detail": False,
        "indexed_only": True,
        "range_label": rng["label"],
    }


class KrakenErrorCatalog:
    """Range-indexed catalog: any KT-CT/KT-GB code in sourced ranges resolves via lookup."""

    def __init__(self) -> None:
        self._detailed: dict[str, KrakenErrorDetail] = {e["code"]: e for e in DETAILED_ENTRIES}

    @property
    def total_codes(self) -> int:
        return DOCUMENTED_TOTAL_CODES

    @property
    def detailed_count(self) -> int:
        return len(self._detailed)

    def get(self, code: str) -> dict[str, Any] | None:
        parsed = _parse_code(code)
        if not parsed:
            return None
        prefix, num = parsed
        detail = self._detailed.get(_code_str(prefix, num))
        if not detail and not _range_for_number(prefix, num):
            return None
        return _index_entry(prefix, num, detail)

    def lookup_by_message(self, message: str) -> dict[str, Any] | None:
        msg = (message or "").strip()
        for entry in DETAILED_ENTRIES:
            if entry["message"] == msg or (entry["message"] and entry["message"] in msg):
                return {**entry, "has_detail": True, "indexed_only": False}
        parsed = _parse_code(msg)
        if parsed:
            return self.get(_code_str(*parsed))
        match = _CODE_RE.search(msg.upper())
        if match:
            return self.get(f"KT-{match.group(1)}-{match.group(2)}")
        return None

    def search(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        phase: str | None = None,
        relevance: str | None = None,
        error_type: str | None = None,
        has_detail: bool | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        q_lower = (q or "").lower()

        for entry in DETAILED_ENTRIES:
            item = {**entry, "has_detail": True, "indexed_only": False}
            if category and item.get("category") != category:
                continue
            if phase and item.get("migration_phase") != phase:
                continue
            if relevance and item.get("migration_relevance") != relevance:
                continue
            if error_type and item.get("error_type") != error_type:
                continue
            if has_detail is False:
                continue
            if q_lower:
                hay = " ".join(
                    str(item.get(k, ""))
                    for k in ("code", "message", "trigger", "category", "error_type")
                ).lower()
                if q_lower not in hay:
                    continue
            results.append(item)
            if len(results) >= limit:
                return results

        if has_detail is True:
            return results

        for rng in ALL_RANGES:
            if category and rng["category"] != category:
                continue
            if phase and rng["default_phase"] != phase:
                continue
            if relevance and rng["migration_relevance"] != relevance:
                continue
            if error_type and error_type != "INDEXED":
                continue
            label = f"{rng['prefix']}-{rng['start']}"
            if rng["end"] != rng["start"]:
                label = f"{rng['prefix']}-{rng['start']}..{rng['end']}"
            if q_lower and q_lower not in label.lower() and q_lower not in rng["label"].lower():
                continue
            results.append(
                {
                    "code": label,
                    "error_type": "INDEXED",
                    "trigger": rng["label"],
                    "message": "",
                    "category": rng["category"],
                    "migration_phase": rng["default_phase"],
                    "migration_relevance": rng["migration_relevance"],
                    "owner_role": rng["default_owner"],
                    "is_blocker": rng["migration_relevance"] in ("high", "medium"),
                    "has_detail": False,
                    "indexed_only": True,
                    "range_start": rng["start"],
                    "range_end": rng["end"],
                }
            )
            if len(results) >= limit:
                break

        return results

    def summary(self) -> dict[str, Any]:
        by_category: dict[str, int] = {}
        by_phase: dict[str, int] = {}
        by_relevance: dict[str, int] = {}
        by_type: dict[str, int] = {}
        pre_migration_blockers = 0

        for entry in DETAILED_ENTRIES:
            by_category[entry["category"]] = by_category.get(entry["category"], 0) + 1
            by_phase[entry["migration_phase"]] = by_phase.get(entry["migration_phase"], 0) + 1
            by_relevance[entry["migration_relevance"]] = by_relevance.get(entry["migration_relevance"], 0) + 1
            by_type[entry["error_type"]] = by_type.get(entry["error_type"], 0) + 1
            if entry.get("migration_phase") == "pre_migration" and entry.get("is_blocker"):
                pre_migration_blockers += 1

        for rng in ALL_RANGES:
            by_category[rng["category"]] = by_category.get(rng["category"], 0) + 1

        return {
            "total_codes": self.total_codes,
            "detailed_entries": self.detailed_count,
            "indexed_ranges": len(ALL_RANGES),
            "categories": {CATEGORY_LABELS.get(k, k): v for k, v in sorted(by_category.items())},
            "by_phase": by_phase,
            "by_relevance": by_relevance,
            "by_error_type": by_type,
            "pre_migration_blockers_indexed": pre_migration_blockers,
            "source": "developer.pwl.kraken.tech/graphql/reference/error-codes",
        }

    def categories(self) -> list[dict[str, str]]:
        return [{"id": k, "label": v} for k, v in CATEGORY_LABELS.items()]

    def pre_migration_codes(self) -> list[dict[str, Any]]:
        return self.search(phase="pre_migration", relevance="high", limit=500)


@lru_cache
def get_kraken_error_catalog() -> KrakenErrorCatalog:
    return KrakenErrorCatalog()
