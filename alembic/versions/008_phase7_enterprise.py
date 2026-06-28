"""Phase 7 — auth, async runs, profiling, exception queue.

Revision ID: 008_phase7
Revises: 007_phase6
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "008_phase7"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(64), nullable=False, server_default="mapping_lead"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.add_column("migration_runs", sa.Column("progress_pct", sa.Integer(), server_default="0"))
    op.add_column("migration_runs", sa.Column("progress_message", sa.String(512), nullable=True))
    op.add_column(
        "migration_runs",
        sa.Column("checkpoint", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "migration_runs",
        sa.Column("execution_mode", sa.String(32), nullable=False, server_default="sync"),
    )

    op.create_table(
        "data_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ingest_file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ingest_files.id", ondelete="CASCADE"), nullable=True),
        sa.Column("entity", sa.String(128), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("column_stats", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("anomalies", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("summary", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_data_profiles_project_id", "data_profiles", ["project_id"])

    op.create_table(
        "exception_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("migration_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ingest_error_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ingest_errors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entity", sa.String(128), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("override_payload", postgresql.JSONB(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("history", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_exception_items_project_id", "exception_items", ["project_id"])
    op.create_index("ix_exception_items_status", "exception_items", ["status"])


def downgrade() -> None:
    op.drop_index("ix_exception_items_status", "exception_items")
    op.drop_index("ix_exception_items_project_id", "exception_items")
    op.drop_table("exception_items")
    op.drop_index("ix_data_profiles_project_id", "data_profiles")
    op.drop_table("data_profiles")
    op.drop_column("migration_runs", "execution_mode")
    op.drop_column("migration_runs", "checkpoint")
    op.drop_column("migration_runs", "progress_message")
    op.drop_column("migration_runs", "progress_pct")
    op.drop_table("users")
