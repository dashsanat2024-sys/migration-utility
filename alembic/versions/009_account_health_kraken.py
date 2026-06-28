"""Phase 8 — account health, Kraken fallout classification."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "009_account_health"
down_revision = "008_phase7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_health_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity", sa.String(128), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cohort_readiness_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("summary", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_account_health_assessments_project_id", "account_health_assessments", ["project_id"])

    op.create_table(
        "account_health_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("account_health_assessments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("readiness_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("readiness_status", sa.String(32), nullable=False, server_default="blocked"),
        sa.Column("findings", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("payload_snapshot", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("has_blocker", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_account_health_records_assessment_id", "account_health_records", ["assessment_id"])
    op.create_index("ix_account_health_records_project_id", "account_health_records", ["project_id"])
    op.create_index("ix_account_health_records_status", "account_health_records", ["readiness_status"])

    op.add_column("exception_items", sa.Column("kraken_error_code", sa.String(32), nullable=True))
    op.add_column("exception_items", sa.Column("root_cause_category", sa.String(64), nullable=True))
    op.add_column("exception_items", sa.Column("owner_role", sa.String(64), nullable=True))
    op.add_column("exception_items", sa.Column("remediation_hint", sa.Text(), nullable=True))
    op.add_column("exception_items", sa.Column("fallout_status", sa.String(32), nullable=False, server_default="open"))
    op.create_index("ix_exception_items_kraken_error_code", "exception_items", ["kraken_error_code"])
    op.create_index("ix_exception_items_root_cause_category", "exception_items", ["root_cause_category"])


def downgrade() -> None:
    op.drop_index("ix_exception_items_root_cause_category", "exception_items")
    op.drop_index("ix_exception_items_kraken_error_code", "exception_items")
    op.drop_column("exception_items", "fallout_status")
    op.drop_column("exception_items", "remediation_hint")
    op.drop_column("exception_items", "owner_role")
    op.drop_column("exception_items", "root_cause_category")
    op.drop_column("exception_items", "kraken_error_code")
    op.drop_index("ix_account_health_records_status", "account_health_records")
    op.drop_index("ix_account_health_records_project_id", "account_health_records")
    op.drop_index("ix_account_health_records_assessment_id", "account_health_records")
    op.drop_table("account_health_records")
    op.drop_index("ix_account_health_assessments_project_id", "account_health_assessments")
    op.drop_table("account_health_assessments")
