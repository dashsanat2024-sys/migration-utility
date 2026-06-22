"""Phase 6 — project field catalogs

Revision ID: 007
Revises: 006
Create Date: 2026-06-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "field_catalogs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity", sa.String(length=128), nullable=False),
        sa.Column("source_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("target_filename", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "entity", name="uq_field_catalog_project_entity"),
    )
    op.create_index(op.f("ix_field_catalogs_project_id"), "field_catalogs", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_field_catalogs_project_id"), table_name="field_catalogs")
    op.drop_table("field_catalogs")
