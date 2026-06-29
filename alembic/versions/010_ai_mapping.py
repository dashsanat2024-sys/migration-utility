"""Phase 9 — AI-assisted mapping metadata on field_mappings."""

from alembic import op
import sqlalchemy as sa

revision = "010_ai_mapping"
down_revision = "009_account_health"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "field_mappings",
        sa.Column("ai_suggested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("field_mappings", sa.Column("ai_reasoning", sa.Text(), nullable=True))
    op.add_column("field_mappings", sa.Column("ai_confidence", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("field_mappings", "ai_confidence")
    op.drop_column("field_mappings", "ai_reasoning")
    op.drop_column("field_mappings", "ai_suggested")
