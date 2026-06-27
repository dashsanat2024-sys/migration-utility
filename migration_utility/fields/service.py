from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from migration_utility.datastore.models import FieldCatalog, Project, RuleSet
from migration_utility.fields.catalog_parser import (
    parse_field_catalog,
    suggest_field_mappings,
    suggest_schema_mappings,
)
from migration_utility.plugins.registry import DestinationPluginRegistry
from migration_utility.schema.registry import SchemaEntity, SchemaField
from migration_utility.schema.target_registry import TargetEntity, TargetField


class FieldCatalogService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_or_create(self, project_id: UUID, entity: str) -> FieldCatalog:
        catalog = self._db.scalar(
            select(FieldCatalog).where(
                FieldCatalog.project_id == project_id,
                FieldCatalog.entity == entity,
            )
        )
        if catalog:
            return catalog
        catalog = FieldCatalog(project_id=project_id, entity=entity)
        self._db.add(catalog)
        self._db.flush()
        return catalog

    def get(self, project_id: UUID, entity: str) -> FieldCatalog | None:
        return self._db.scalar(
            select(FieldCatalog).where(
                FieldCatalog.project_id == project_id,
                FieldCatalog.entity == entity,
            )
        )

    def upload_source(
        self,
        project: Project,
        entity: str,
        *,
        text: str,
        filename: str,
        content_type: str | None = None,
    ) -> FieldCatalog:
        fields = parse_field_catalog(text, filename=filename, content_type=content_type)
        catalog = self.get_or_create(project.id, entity)
        catalog.source_fields = fields
        catalog.source_filename = filename
        self._db.commit()
        self._db.refresh(catalog)
        return catalog

    def upload_target(
        self,
        project: Project,
        entity: str,
        *,
        text: str,
        filename: str,
        content_type: str | None = None,
    ) -> FieldCatalog:
        fields = parse_field_catalog(text, filename=filename, content_type=content_type)
        catalog = self.get_or_create(project.id, entity)
        catalog.target_fields = fields
        catalog.target_filename = filename
        self._db.commit()
        self._db.refresh(catalog)
        return catalog

    def clear_target(self, project_id: UUID, entity: str) -> FieldCatalog | None:
        catalog = self.get(project_id, entity)
        if not catalog:
            return None
        catalog.target_fields = []
        catalog.target_filename = None
        self._db.commit()
        self._db.refresh(catalog)
        return catalog

    def resolve_destination_fields(
        self,
        project: Project,
        entity: str,
        plugin_registry: DestinationPluginRegistry,
    ) -> list[dict[str, Any]]:
        catalog = self.get(project.id, entity)
        if catalog and catalog.target_fields:
            return catalog.target_fields
        plugin = plugin_registry.resolve_for_project(project)
        schema = plugin.get_schema(entity)
        if not schema:
            raise ValueError(f"Plugin {plugin.id!r} has no schema for entity {entity!r}")
        return schema.to_catalog_fields()

    def suggest_mappings(
        self,
        project_id: UUID,
        entity: str,
        *,
        project: Project | None = None,
        plugin_registry: DestinationPluginRegistry | None = None,
        destination_first: bool = False,
    ) -> list[dict[str, Any]]:
        catalog = self.get(project_id, entity)
        if not catalog or not catalog.source_fields:
            raise ValueError("Upload source fields before suggesting mappings")

        target_fields: list[dict[str, Any]] | None = None
        if catalog.target_fields:
            target_fields = catalog.target_fields
        elif project and plugin_registry:
            target_fields = self.resolve_destination_fields(project, entity, plugin_registry)

        if not target_fields:
            raise ValueError(
                "No destination schema available — configure a destination plugin or upload target fields"
            )

        if destination_first:
            return suggest_schema_mappings(catalog.source_fields, target_fields)
        return suggest_field_mappings(catalog.source_fields, target_fields)

    def apply_mappings_to_rule_set(
        self,
        rule_set: RuleSet,
        mappings: list[dict[str, Any]],
    ) -> RuleSet:
        if rule_set.workflow_state not in ("draft", "in_review"):
            raise ValueError("Mappings are locked after approval")

        for mapping in list(rule_set.field_mappings):
            self._db.delete(mapping)
        self._db.flush()

        order = 0
        for row in mappings:
            target_field = row.get("target_field")
            if not target_field:
                continue
            order += 1
            from migration_utility.datastore.models import FieldMapping

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

    @staticmethod
    def resolve_source_entity(catalog: FieldCatalog | None, default: SchemaEntity | None) -> SchemaEntity | None:
        if catalog and catalog.source_fields:
            return SchemaEntity(
                name=catalog.entity,
                fields=[
                    SchemaField(
                        f["name"],
                        f.get("data_type", "string"),
                        required=bool(f.get("required", False)),
                        description=f.get("description", ""),
                    )
                    for f in catalog.source_fields
                ],
            )
        return default

    @staticmethod
    def resolve_target_entity(
        catalog: FieldCatalog | None,
        default: TargetEntity | None,
    ) -> TargetEntity | None:
        if catalog and catalog.target_fields:
            return TargetEntity(
                name=catalog.entity,
                fields=[
                    TargetField(
                        f["name"],
                        f.get("data_type", "string"),
                        required=bool(f.get("required", False)),
                        description=f.get("description", ""),
                    )
                    for f in catalog.target_fields
                ],
            )
        return default
