from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from migration_utility.datastore.base import Base, TimestampMixin, new_uuid
from migration_utility.workflow import MappingWorkflowState


class RuleSet(Base, TimestampMixin):
    __tablename__ = "rule_sets"
    __table_args__ = (
        UniqueConstraint("project_id", "entity", "version", name="uq_rule_set_project_entity_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    workflow_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=MappingWorkflowState.DRAFT.value
    )

    validation_rules: Mapped[list["ValidationRule"]] = relationship(
        back_populates="rule_set", cascade="all, delete-orphan"
    )
    field_mappings: Mapped[list["FieldMapping"]] = relationship(
        back_populates="rule_set", cascade="all, delete-orphan"
    )


class ValidationRule(Base, TimestampMixin):
    __tablename__ = "validation_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    rule_set: Mapped["RuleSet"] = relationship(back_populates="validation_rules")


class FieldMapping(Base, TimestampMixin):
    __tablename__ = "field_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_field: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_field: Mapped[str] = mapped_column(String(128), nullable=False)
    transform_type: Mapped[str] = mapped_column(String(64), nullable=False, default="copy")
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    rule_set: Mapped["RuleSet"] = relationship(back_populates="field_mappings")
