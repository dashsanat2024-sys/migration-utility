from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from migration_utility.datastore.base import Base, TimestampMixin, new_uuid
from migration_utility.workflow import MappingWorkflowState

if TYPE_CHECKING:
    from migration_utility.datastore.models.project import Project


class TariffMappingSet(Base, TimestampMixin):
    __tablename__ = "tariff_mapping_sets"
    __table_args__ = (
        UniqueConstraint("project_id", "version", name="uq_tariff_set_project_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    workflow_state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=MappingWorkflowState.DRAFT.value
    )
    loaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="tariff_mapping_sets")
    mappings: Mapped[list["TariffMapping"]] = relationship(
        back_populates="tariff_set", cascade="save-update, merge"
    )


class TariffMapping(Base, TimestampMixin):
    __tablename__ = "tariff_mappings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    tariff_set_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tariff_mapping_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_code: Mapped[str] = mapped_column(String(128), nullable=False)
    target_code: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tariff_set: Mapped["TariffMappingSet"] = relationship(back_populates="mappings")
