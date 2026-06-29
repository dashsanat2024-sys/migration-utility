"""Phase 4 — load_records idempotency index.

Revision ID: 012_load_audit_index
Revises: 011_parallel_workers
"""

from alembic import op

revision = "012_load_audit_index"
down_revision = "011_parallel_workers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_load_records_project_entity_status",
        "load_records",
        ["project_id", "entity", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_load_records_project_entity_status", table_name="load_records")
