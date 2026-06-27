from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from migration_utility.datastore.models import FieldMapping, Project, RuleSet
from migration_utility.fields.service import FieldCatalogService
from migration_utility.plugins.registry import DestinationPluginRegistry
from migration_utility.schema.registry import SchemaRegistry
from migration_utility.schema.target_registry import TargetField, TargetSchemaRegistry


class MappingMatrixService:
    """Build and update the source → target mapping matrix."""

    _EDITABLE_STATES = {"draft", "in_review"}

    def __init__(
        self,
        db: Session,
        source_registry: SchemaRegistry,
        target_registry: TargetSchemaRegistry,
        plugin_registry: DestinationPluginRegistry | None = None,
    ) -> None:
        self._db = db
        self._source_registry = source_registry
        self._target_registry = target_registry
        self._plugin_registry = plugin_registry

    def _resolve_target_fields(self, project: Project, entity: str, catalog) -> list:
        if catalog and catalog.target_fields:
            return [
                TargetField(
                    f["name"],
                    f.get("data_type", "string"),
                    required=bool(f.get("required", False)),
                    description=f.get("description", ""),
                )
                for f in catalog.target_fields
            ]
        if self._plugin_registry:
            try:
                raw = FieldCatalogService(self._db).resolve_destination_fields(
                    project, entity, self._plugin_registry
                )
                return [
                    TargetField(
                        f["name"],
                        f.get("data_type", "string"),
                        required=bool(f.get("required", False)),
                        description=f.get("description", ""),
                    )
                    for f in raw
                ]
            except (ValueError, KeyError):
                pass
        target = self._target_registry.get(project.target_system, entity)
        return target.fields if target else []

    def get_matrix(self, project: Project, rule_set: RuleSet) -> dict[str, Any]:
        catalog = FieldCatalogService(self._db).get(project.id, rule_set.entity)
        source = FieldCatalogService.resolve_source_entity(
            catalog, self._source_registry.get(rule_set.entity)
        )
        target_fields_raw = self._resolve_target_fields(project, rule_set.entity, catalog)
        source_fields = source.fields if source else []
        target_fields = target_fields_raw

        by_source = {m.source_field: m for m in rule_set.field_mappings if m.source_field}
        by_target = {m.target_field: m for m in rule_set.field_mappings}

        rows: list[dict[str, Any]] = []
        for sf in source_fields:
            mapping = by_source.get(sf.name)
            rows.append(
                {
                    "source_field": sf.name,
                    "source_type": sf.data_type,
                    "source_required": sf.required,
                    "target_field": mapping.target_field if mapping else None,
                    "transform_type": mapping.transform_type if mapping else "copy",
                    "config": mapping.config if mapping else {},
                    "mapping_id": str(mapping.id) if mapping else None,
                    "enabled": mapping.enabled if mapping else True,
                    "status": "mapped" if mapping else "unmapped",
                }
            )

        for tf in target_fields:
            if tf.name not in by_target and not any(r["target_field"] == tf.name for r in rows):
                rows.append(
                    {
                        "source_field": None,
                        "source_type": None,
                        "source_required": False,
                        "target_field": tf.name,
                        "transform_type": "constant",
                        "config": {},
                        "mapping_id": None,
                        "enabled": False,
                        "status": "target_only",
                    }
                )

        mapped_targets = {r["target_field"] for r in rows if r["target_field"]}
        unmapped_targets = [f.name for f in target_fields if f.name not in mapped_targets]

        return {
            "entity": rule_set.entity,
            "rule_set_id": str(rule_set.id),
            "workflow_state": rule_set.workflow_state,
            "editable": rule_set.workflow_state in self._EDITABLE_STATES,
            "source_fields": [
                {"name": f.name, "data_type": f.data_type, "required": f.required}
                for f in source_fields
            ],
            "target_fields": [
                {"name": f.name, "data_type": f.data_type, "required": f.required}
                for f in target_fields
            ],
            "rows": rows,
            "coverage": {
                "source_mapped": sum(1 for r in rows if r["status"] == "mapped"),
                "source_total": len(source_fields),
                "unmapped_targets": unmapped_targets,
            },
            "field_catalog": {
                "has_source": bool(catalog and catalog.source_fields),
                "has_target": bool(catalog and catalog.target_fields) or bool(target_fields),
                "source_filename": catalog.source_filename if catalog else None,
                "target_filename": catalog.target_filename if catalog else None,
                "source_count": len(catalog.source_fields) if catalog else 0,
                "target_count": len(target_fields),
                "schema_from_plugin": bool(
                    (not catalog or not catalog.target_fields) and target_fields and self._plugin_registry
                ),
            },
        }

    def upsert_mappings(
        self,
        rule_set: RuleSet,
        rows: list[dict[str, Any]],
    ) -> RuleSet:
        if rule_set.workflow_state not in self._EDITABLE_STATES:
            raise ValueError("Mappings are locked after approval")

        for mapping in list(rule_set.field_mappings):
            self._db.delete(mapping)
        self._db.flush()

        order = 0
        for row in rows:
            target_field = row.get("target_field")
            if not target_field:
                continue
            order += 1
            self._db.add(
                FieldMapping(
                    rule_set_id=rule_set.id,
                    source_field=row.get("source_field"),
                    target_field=target_field,
                    transform_type=row.get("transform_type", "copy"),
                    config=row.get("config") or {},
                    enabled=row.get("enabled", True),
                    sort_order=order,
                )
            )

        self._db.commit()
        self._db.refresh(rule_set)
        return rule_set
