"""Phase 5 — target load records

Revision ID: 006
Revises: 005
Create Date: 2026-06-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "load_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_adapter_key", sa.String(length=128), nullable=False),
        sa.Column("entity", sa.String(length=128), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["migration_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_load_records_batch_id"), "load_records", ["batch_id"], unique=False)
    op.create_index(op.f("ix_load_records_external_id"), "load_records", ["external_id"], unique=False)
    op.create_index(op.f("ix_load_records_project_id"), "load_records", ["project_id"], unique=False)
    op.create_index(op.f("ix_load_records_run_id"), "load_records", ["run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_load_records_run_id"), table_name="load_records")
    op.drop_index(op.f("ix_load_records_project_id"), table_name="load_records")
    op.drop_index(op.f("ix_load_records_external_id"), table_name="load_records")
    op.drop_index(op.f("ix_load_records_batch_id"), table_name="load_records")
    op.drop_table("load_records")
