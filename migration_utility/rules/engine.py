from __future__ import annotations

import re
from typing import Any

from migration_utility.rules.types import FieldMappingDef, LoadedRuleSet, ValidationRuleDef


class ValidationEngine:
    """Apply configurable validation rules to record batches."""

    def apply(
        self,
        records: list[dict[str, Any]],
        rules: list[ValidationRuleDef],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
        if not rules:
            return records, [], []

        enabled = [r for r in rules if r.enabled]
        valid: list[dict[str, Any]] = []
        invalid: list[dict[str, Any]] = []
        reasons: list[str] = []

        seen_unique: dict[str, set[Any]] = {r.field_name or "": set() for r in enabled if r.rule_type == "unique"}

        for record in records:
            errors = self._validate_record(record, enabled, seen_unique)
            if errors:
                invalid.append(record)
                reasons.append("; ".join(errors))
            else:
                valid.append(record)

        return valid, invalid, reasons

    def _validate_record(
        self,
        record: dict[str, Any],
        rules: list[ValidationRuleDef],
        seen_unique: dict[str, set[Any]],
    ) -> list[str]:
        errors: list[str] = []
        for rule in rules:
            err = self._apply_rule(record, rule, seen_unique)
            if err:
                errors.append(err)
        return errors

    def _apply_rule(
        self,
        record: dict[str, Any],
        rule: ValidationRuleDef,
        seen_unique: dict[str, set[Any]],
    ) -> str | None:
        rt = rule.rule_type
        cfg = rule.config
        fname = rule.field_name

        if rt == "required":
            if fname and _is_empty(record.get(fname)):
                return f"{rule.name}: missing required field {fname!r}"
        elif rt == "format":
            if fname and not _is_empty(record.get(fname)):
                pattern = cfg.get("pattern", "")
                if pattern and not re.match(pattern, str(record[fname])):
                    return f"{rule.name}: {fname!r} does not match pattern {pattern!r}"
        elif rt == "in_list":
            if fname and not _is_empty(record.get(fname)):
                allowed = cfg.get("values", [])
                if str(record[fname]) not in {str(v) for v in allowed}:
                    return f"{rule.name}: {fname!r} must be one of {allowed}"
        elif rt == "range":
            if fname and not _is_empty(record.get(fname)):
                try:
                    val = float(record[fname])
                except (TypeError, ValueError):
                    return f"{rule.name}: {fname!r} is not numeric"
                if "min" in cfg and val < cfg["min"]:
                    return f"{rule.name}: {fname!r} below minimum {cfg['min']}"
                if "max" in cfg and val > cfg["max"]:
                    return f"{rule.name}: {fname!r} above maximum {cfg['max']}"
        elif rt == "cross_field":
            if_field = cfg.get("if_field")
            if_equals = cfg.get("if_equals")
            if if_field and str(record.get(if_field)) == str(if_equals):
                for req in cfg.get("then_required", []):
                    if _is_empty(record.get(req)):
                        return f"{rule.name}: {req!r} required when {if_field}={if_equals!r}"
        elif rt == "unique":
            if fname and not _is_empty(record.get(fname)):
                val = record[fname]
                bucket = seen_unique.setdefault(fname, set())
                if val in bucket:
                    return f"{rule.name}: duplicate value {val!r} for {fname!r}"
                bucket.add(val)
        return None


class TransformEngine:
    """Apply field mappings and transform rules to produce target payloads."""

    def apply(
        self,
        records: list[dict[str, Any]],
        mappings: list[FieldMappingDef],
        *,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        enabled = sorted([m for m in mappings if m.enabled], key=lambda m: m.sort_order)
        if not enabled:
            return [dict(r) for r in records]

        ctx = context or {}
        return [self._transform_one(record, enabled, ctx) for record in records]

    def _transform_one(
        self,
        record: dict[str, Any],
        mappings: list[FieldMappingDef],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        working = dict(record)
        out: dict[str, Any] = {}
        for mapping in mappings:
            value = self._apply_mapping(working, out, mapping, context)
            out[mapping.target_field] = value
            if value is not None:
                working[mapping.target_field] = value
        return out

    def _apply_mapping(
        self,
        source: dict[str, Any],
        target_so_far: dict[str, Any],
        mapping: FieldMappingDef,
        context: dict[str, Any],
    ) -> Any:
        tt = mapping.transform_type
        cfg = mapping.config
        src = mapping.source_field

        if tt == "copy":
            return source.get(src) if src else None
        if tt == "constant":
            return cfg.get("value")
        if tt == "default":
            val = source.get(src) if src else None
            return val if not _is_empty(val) else cfg.get("value")
        if tt == "lookup":
            val = source.get(src) if src else None
            table = cfg.get("map", {})
            return table.get(str(val), cfg.get("default", val))
        if tt == "concat":
            parts = [str(source.get(f, "")) for f in cfg.get("fields", [])]
            sep = cfg.get("separator", " ")
            return sep.join(p for p in parts if p)
        if tt == "conditional":
            when = cfg.get("when", {})
            field = when.get("field")
            if field and str(source.get(field)) == str(when.get("equals")):
                return cfg.get("then")
            return cfg.get("else")
        if tt == "uppercase":
            val = source.get(src) if src else None
            return str(val).upper() if val is not None else None
        if tt == "lowercase":
            val = source.get(src) if src else None
            return str(val).lower() if val is not None else None
        if tt == "date_format":
            from datetime import datetime

            val = source.get(src) if src else None
            if _is_empty(val):
                return None
            inp = cfg.get("input_format", "%Y-%m-%d")
            out_fmt = cfg.get("output_format", "%d/%m/%Y")
            if isinstance(val, str) and inp:
                dt = datetime.strptime(val[:10], inp)
            else:
                dt = datetime.fromisoformat(str(val)[:10])
            return dt.strftime(out_fmt)
        if tt == "pad_left":
            val = source.get(src) if src else None
            if _is_empty(val):
                return val
            width = int(cfg.get("width", 9))
            char = str(cfg.get("char", "0"))
            text = str(val).strip()
            return text if len(text) >= width else char * (width - len(text)) + text
        if tt == "regex_replace":
            val = source.get(src) if src else None
            if val is None:
                return None
            pattern = cfg.get("pattern", "")
            replacement = cfg.get("replacement", "")
            if pattern:
                return re.sub(pattern, replacement, str(val))
            return val
        if tt == "stw_property_type":
            from migration_utility.transforms.stw import transform_property_type

            rules = self._stw_rules(context, "property_type", cfg)
            return transform_property_type(source, rules)
        if tt == "stw_area_code":
            from migration_utility.transforms.stw import transform_area_code

            rules = self._stw_rules(context, "area_code", cfg)
            return transform_area_code(source, rules, context=context)
        if tt == "stw_rateband_lookup":
            from migration_utility.transforms.stw import transform_rateband

            rules = self._stw_rules(context, "rateband", cfg)
            row = transform_rateband(source, rules)
            if not row:
                return cfg.get("default")
            output_key = cfg.get("output_key", "kraken_rate_band")
            return row.get(output_key) or row.get("rate_band") or cfg.get("default")
        return source.get(src) if src else None

    @staticmethod
    def _stw_rules(context: dict[str, Any], rule_key: str, cfg: dict[str, Any]) -> dict[str, Any]:
        base = (context.get("stw_transform_rules") or {}).get(rule_key) or {}
        override = cfg.get("rules") or {}
        if not override:
            return base
        merged = dict(base)
        merged.update(override)
        return merged


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")
