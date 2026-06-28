from __future__ import annotations

import re
from collections import Counter
from typing import Any


def profile_records(records: list[dict[str, Any]], *, entity: str) -> dict[str, Any]:
    if not records:
        return {
            "entity": entity,
            "row_count": 0,
            "column_stats": [],
            "anomalies": [],
            "summary": {"message": "No rows to profile"},
        }

    columns: dict[str, list[Any]] = {}
    for row in records:
        for key, value in row.items():
            columns.setdefault(key, []).append(value)

    column_stats: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    row_count = len(records)

    for name, values in sorted(columns.items()):
        non_null = [v for v in values if v is not None and str(v).strip() != ""]
        null_count = row_count - len(non_null)
        null_pct = round(100 * null_count / row_count, 2)
        distinct = len({str(v) for v in non_null})
        samples = [str(v) for v in non_null[:3]]
        inferred = _infer_type(non_null)
        stat = {
            "column": name,
            "inferred_type": inferred,
            "null_count": null_count,
            "null_pct": null_pct,
            "distinct_count": distinct,
            "sample_values": samples,
        }
        column_stats.append(stat)

        if null_pct >= 50:
            anomalies.append(
                {
                    "column": name,
                    "severity": "high",
                    "type": "high_null_rate",
                    "message": f"{null_pct}% null/empty values in column {name!r}",
                }
            )
        if distinct == 1 and len(non_null) > 1:
            anomalies.append(
                {
                    "column": name,
                    "severity": "medium",
                    "type": "constant_column",
                    "message": f"Column {name!r} has a single distinct value across {row_count} rows",
                }
            )
        if inferred == "numeric":
            nums = _numeric_values(non_null)
            if nums:
                stat["min"] = min(nums)
                stat["max"] = max(nums)
                if stat["min"] == stat["max"]:
                    anomalies.append(
                        {
                            "column": name,
                            "severity": "low",
                            "type": "flat_numeric",
                            "message": f"Numeric column {name!r} has no variance",
                        }
                    )

    unique_rows = {tuple(sorted((k, str(v)) for k, v in r.items())) for r in records}
    duplicate_rows = row_count - len(unique_rows)
    if duplicate_rows > 0:
        anomalies.append(
            {
                "column": "*",
                "severity": "medium",
                "type": "duplicate_rows",
                "message": f"{duplicate_rows} potential duplicate row(s) detected",
            }
        )

    return {
        "entity": entity,
        "row_count": row_count,
        "column_stats": column_stats,
        "anomalies": anomalies,
        "summary": {
            "column_count": len(column_stats),
            "anomaly_count": len(anomalies),
            "high_severity_count": sum(1 for a in anomalies if a.get("severity") == "high"),
        },
    }


def _infer_type(values: list[Any]) -> str:
    if not values:
        return "unknown"
    numeric = sum(1 for v in values if _is_numeric(v))
    if numeric >= max(1, len(values) * 0.8):
        return "numeric"
    dates = sum(1 for v in values if _looks_like_date(str(v)))
    if dates >= max(1, len(values) * 0.6):
        return "date"
    return "string"


def _is_numeric(value: Any) -> bool:
    try:
        float(str(value).replace(",", ""))
        return True
    except ValueError:
        return False


def _numeric_values(values: list[Any]) -> list[float]:
    out: list[float] = []
    for v in values:
        try:
            out.append(float(str(v).replace(",", "")))
        except ValueError:
            continue
    return out


def _looks_like_date(value: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}", value) or re.match(r"^\d{2}/\d{2}/\d{4}", value))
