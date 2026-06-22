import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from migration_utility.datastore.base import Base, TimestampMixin, new_uuid


class FieldCatalog(Base, TimestampMixin):
    """Per-project uploaded source and target field definitions for mapping."""

    __tablename__ = "field_catalogs"
    __table_args__ = (
        UniqueConstraint("project_id", "entity", name="uq_field_catalog_project_entity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity: Mapped[str] = mapped_column(String(128), nullable=False)
    source_fields: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    target_fields: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
