import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from migration_utility.core.enums import BatchStatus
from migration_utility.datastore.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from migration_utility.datastore.models.candidate import Candidate
    from migration_utility.datastore.models.migration_run import MigrationRun


class Batch(Base, TimestampMixin):
    __tablename__ = "batches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("migration_runs.id", ondelete="CASCADE"), nullable=False
    )
    batch_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=BatchStatus.PENDING.value
    )
    batch_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    stats: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    run: Mapped["MigrationRun"] = relationship(back_populates="batches")
    candidates: Mapped[list["Candidate"]] = relationship(
        back_populates="batch", cascade="save-update, merge"
    )
