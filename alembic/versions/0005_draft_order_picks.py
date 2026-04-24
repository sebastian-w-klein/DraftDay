"""add draft order picks table

Revision ID: 0005_draft_order_picks
Revises: 0004_org_intelligence_tables
Create Date: 2026-04-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_draft_order_picks"
down_revision: str | None = "0004_org_intelligence_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "draft_order_picks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_cycle_id", sa.Integer(), sa.ForeignKey("draft_cycles.id"), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("overall_pick", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("source_name", sa.String(128), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_draft_order_picks_draft_cycle_id", "draft_order_picks", ["draft_cycle_id"])
    op.create_index("ix_draft_order_picks_round_number", "draft_order_picks", ["round_number"])
    op.create_index("ix_draft_order_picks_overall_pick", "draft_order_picks", ["overall_pick"])
    op.create_index("ix_draft_order_picks_team_id", "draft_order_picks", ["team_id"])
    op.create_index(
        "uq_draft_order_picks_cycle_pick",
        "draft_order_picks",
        ["draft_cycle_id", "overall_pick"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_draft_order_picks_cycle_pick", table_name="draft_order_picks")
    op.drop_index("ix_draft_order_picks_team_id", table_name="draft_order_picks")
    op.drop_index("ix_draft_order_picks_overall_pick", table_name="draft_order_picks")
    op.drop_index("ix_draft_order_picks_round_number", table_name="draft_order_picks")
    op.drop_index("ix_draft_order_picks_draft_cycle_id", table_name="draft_order_picks")
    op.drop_table("draft_order_picks")
