import uuid
from typing import TYPE_CHECKING, Any

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from migration_utility.core.enums import RunStatus
from migration_utility.datastore.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from migration_utility.datastore.models.batch import Batch
    from migration_utility.datastore.models.project import Project


class MigrationRun(Base, TimestampMixin):
    __tablename__ = "migration_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=RunStatus.PENDING.value
    )
    run_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    result_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    progress_pct: Mapped[int] = mapped_column(default=0)
    progress_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    checkpoint: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    execution_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="sync")

    project: Mapped["Project"] = relationship(back_populates="runs")
    batches: Mapped[list["Batch"]] = relationship(
        back_populates="run", cascade="save-update, merge"
    )
