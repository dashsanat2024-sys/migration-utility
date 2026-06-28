"""Merge project overrides with STW default transform rules."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from migration_utility.transforms.stw.defaults import DEFAULT_STW_TRANSFORM_RULES


def _deep_merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def get_stw_rules(project_config: dict | None) -> dict[str, Any]:
    stored = (project_config or {}).get("stw_transform_rules") or {}
    return {
        key: _deep_merge(DEFAULT_STW_TRANSFORM_RULES[key], stored.get(key) or {})
        for key in DEFAULT_STW_TRANSFORM_RULES
    }


def update_stw_rule(project_config: dict | None, rule_key: str, patch: dict) -> dict[str, Any]:
    cfg = dict(project_config or {})
    current = cfg.get("stw_transform_rules") or {}
    stored = current.get(rule_key) or {}
    current[rule_key] = _deep_merge(stored, patch)
    cfg["stw_transform_rules"] = current
    return cfg
