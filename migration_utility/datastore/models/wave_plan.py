"""Migration wave plan — orchestrates multiple queued runs per day."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from migration_utility.datastore.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from migration_utility.datastore.models.project import Project


class MigrationWavePlan(Base, TimestampMixin):
    __tablename__ = "migration_wave_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    plan_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    total_waves: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    waves_queued: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    waves_completed: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    waves_failed: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    pause_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("migration_runs.id", ondelete="SET NULL"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship()
