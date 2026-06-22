from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from migration_utility.datastore.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from migration_utility.datastore.models.migration_run import MigrationRun
    from migration_utility.datastore.models.selection import SelectionProfile
    from migration_utility.datastore.models.tariff import TariffMappingSet


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=new_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_system: Mapped[str] = mapped_column(String(128), nullable=False, default="generic")
    source_connector_key: Mapped[str] = mapped_column(String(128), nullable=False, default="mock")
    target_adapter_key: Mapped[str] = mapped_column(String(128), nullable=False, default="mock")
    environment: Mapped[str] = mapped_column(String(64), nullable=False, default="dev")
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    runs: Mapped[list["MigrationRun"]] = relationship(back_populates="project")
    selection_profiles: Mapped[list["SelectionProfile"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    tariff_mapping_sets: Mapped[list["TariffMappingSet"]] = relationship(
        back_populates="project", cascade="save-update, merge"
    )

    def __repr__(self) -> str:
        return f"<Project slug={self.slug!r} env={self.environment!r}>"
