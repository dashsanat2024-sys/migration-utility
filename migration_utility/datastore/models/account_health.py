import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from migration_utility.datastore.base import Base, TimestampMixin, new_uuid


class AccountHealthAssessment(Base, TimestampMixin):
    __tablename__ = "account_health_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity: Mapped[str] = mapped_column(String(128), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cohort_readiness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class AccountHealthRecord(Base, TimestampMixin):
    __tablename__ = "account_health_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("account_health_assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    readiness_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    readiness_status: Mapped[str] = mapped_column(String(32), nullable=False, default="blocked")
    findings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    payload_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    has_blocker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
