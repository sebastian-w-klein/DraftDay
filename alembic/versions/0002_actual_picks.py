"""add actual draft picks table

Revision ID: 0002_actual_picks
Revises: 0001_initial_schema
Create Date: 2026-04-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_actual_picks"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "actual_draft_picks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_cycle_id", sa.Integer(), sa.ForeignKey("draft_cycles.id"), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("overall_pick", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
        sa.Column("normalized_player_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_actual_draft_picks_draft_cycle_id", "actual_draft_picks", ["draft_cycle_id"])
    op.create_index("ix_actual_draft_picks_overall_pick", "actual_draft_picks", ["overall_pick"])
    op.create_index(
        "ix_actual_draft_picks_normalized_player_name",
        "actual_draft_picks",
        ["normalized_player_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_actual_draft_picks_normalized_player_name", table_name="actual_draft_picks")
    op.drop_index("ix_actual_draft_picks_overall_pick", table_name="actual_draft_picks")
    op.drop_index("ix_actual_draft_picks_draft_cycle_id", table_name="actual_draft_picks")
    op.drop_table("actual_draft_picks")
