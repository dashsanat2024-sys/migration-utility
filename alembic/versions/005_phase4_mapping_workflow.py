"""Phase 4 — mapping approvals, tariff mapping sets

Revision ID: 005
Revises: 004
Create Date: 2026-06-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mapping_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_state", sa.String(length=32), nullable=False),
        sa.Column("to_state", sa.String(length=32), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mapping_approvals_entity_id"), "mapping_approvals", ["entity_id"], unique=False)
    op.create_index(op.f("ix_mapping_approvals_project_id"), "mapping_approvals", ["project_id"], unique=False)

    op.create_table(
        "tariff_mapping_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("workflow_state", sa.String(length=32), nullable=False),
        sa.Column("loaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "version", name="uq_tariff_set_project_version"),
    )
    op.create_index(op.f("ix_tariff_mapping_sets_project_id"), "tariff_mapping_sets", ["project_id"], unique=False)

    op.create_table(
        "tariff_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tariff_set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_code", sa.String(length=128), nullable=False),
        sa.Column("target_code", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tariff_set_id"], ["tariff_mapping_sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tariff_mappings_tariff_set_id"), "tariff_mappings", ["tariff_set_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tariff_mappings_tariff_set_id"), table_name="tariff_mappings")
    op.drop_table("tariff_mappings")
    op.drop_index(op.f("ix_tariff_mapping_sets_project_id"), table_name="tariff_mapping_sets")
    op.drop_table("tariff_mapping_sets")
    op.drop_index(op.f("ix_mapping_approvals_project_id"), table_name="mapping_approvals")
    op.drop_index(op.f("ix_mapping_approvals_entity_id"), table_name="mapping_approvals")
    op.drop_table("mapping_approvals")
