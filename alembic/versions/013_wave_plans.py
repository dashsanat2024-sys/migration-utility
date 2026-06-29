"""Phase 5 — migration wave orchestration plans.

Revision ID: 013_wave_plans
Revises: 012_load_audit_index
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "013_wave_plans"
down_revision = "012_load_audit_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "migration_wave_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column(
            "plan_config",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("total_waves", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("waves_queued", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("waves_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("waves_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pause_reason", sa.Text(), nullable=True),
        sa.Column(
            "last_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("migration_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_migration_wave_plans_project_id", "migration_wave_plans", ["project_id"])
    op.create_index("ix_migration_wave_plans_status", "migration_wave_plans", ["status"])


def downgrade() -> None:
    op.drop_index("ix_migration_wave_plans_status", table_name="migration_wave_plans")
    op.drop_index("ix_migration_wave_plans_project_id", table_name="migration_wave_plans")
    op.drop_table("migration_wave_plans")
