import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from migration_utility.datastore.base import Base, TimestampMixin, new_uuid


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="mapping_lead")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DataProfile(Base, TimestampMixin):
    __tablename__ = "data_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ingest_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingest_files.id", ondelete="CASCADE"), nullable=True
    )
    entity: Mapped[str] = mapped_column(String(128), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    column_stats: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    anomalies: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    summary: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class ExceptionItem(Base, TimestampMixin):
    __tablename__ = "exception_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("migration_runs.id", ondelete="SET NULL"), nullable=True
    )
    ingest_error_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingest_errors.id", ondelete="SET NULL"), nullable=True
    )
    entity: Mapped[str] = mapped_column(String(128), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    override_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
