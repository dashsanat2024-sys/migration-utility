"""Phase 3 — parallel worker claim + load idempotency keys.

Revision ID: 011_parallel_workers
Revises: 010_ai_mapping
"""

from alembic import op
import sqlalchemy as sa

revision = "011_parallel_workers"
down_revision = "010_ai_mapping"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("migration_runs", sa.Column("claimed_by", sa.String(128), nullable=True))
    op.add_column(
        "migration_runs",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_migration_runs_claimed_by", "migration_runs", ["claimed_by"])
    op.add_column("load_records", sa.Column("idempotency_key", sa.String(255), nullable=True))
    op.create_index("ix_load_records_idempotency_key", "load_records", ["idempotency_key"])


def downgrade() -> None:
    op.drop_index("ix_load_records_idempotency_key", table_name="load_records")
    op.drop_column("load_records", "idempotency_key")
    op.drop_index("ix_migration_runs_claimed_by", table_name="migration_runs")
    op.drop_column("migration_runs", "claimed_at")
    op.drop_column("migration_runs", "claimed_by")
