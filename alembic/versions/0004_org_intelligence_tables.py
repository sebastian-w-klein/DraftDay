"""add organizational intelligence tables

Revision ID: 0004_org_intelligence_tables
Revises: 0003_draft_intelligence_tables
Create Date: 2026-04-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_org_intelligence_tables"
down_revision: str | None = "0003_draft_intelligence_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "general_managers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_general_managers_normalized_name", "general_managers", ["normalized_name"], unique=True)

    op.create_table(
        "head_coaches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_head_coaches_normalized_name", "head_coaches", ["normalized_name"], unique=True)

    op.create_table(
        "team_front_office_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_cycle_id", sa.Integer(), sa.ForeignKey("draft_cycles.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("general_manager_id", sa.Integer(), sa.ForeignKey("general_managers.id"), nullable=True),
        sa.Column("head_coach_id", sa.Integer(), sa.ForeignKey("head_coaches.id"), nullable=True),
        sa.Column("gm_tenure_year", sa.Integer(), nullable=True),
        sa.Column("hc_tenure_year", sa.Integer(), nullable=True),
        sa.Column("control_regime_label", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_team_front_office_history_draft_cycle_id", "team_front_office_history", ["draft_cycle_id"])
    op.create_index("ix_team_front_office_history_team_id", "team_front_office_history", ["team_id"])

    op.create_table(
        "gm_draft_history_features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("general_manager_id", sa.Integer(), sa.ForeignKey("general_managers.id"), nullable=False),
        sa.Column("draft_cycle_id", sa.Integer(), sa.ForeignKey("draft_cycles.id"), nullable=False),
        sa.Column("years_of_prior_draft_history", sa.Integer(), nullable=False),
        sa.Column("total_prior_picks", sa.Integer(), nullable=False),
        sa.Column("avg_pick_value_spent_offense", sa.Numeric(6, 4), nullable=True),
        sa.Column("avg_pick_value_spent_defense", sa.Numeric(6, 4), nullable=True),
        sa.Column("pct_first_round_trenches", sa.Numeric(6, 4), nullable=True),
        sa.Column("pct_first_round_skill", sa.Numeric(6, 4), nullable=True),
        sa.Column("pct_picks_same_side_as_top_need", sa.Numeric(6, 4), nullable=True),
        sa.Column("pct_picks_best_player_available_proxy", sa.Numeric(6, 4), nullable=True),
        sa.Column("pct_early_round_trades_up", sa.Numeric(6, 4), nullable=True),
        sa.Column("pct_early_round_trades_down", sa.Numeric(6, 4), nullable=True),
        sa.Column("avg_positional_value_of_picks", sa.Numeric(6, 4), nullable=True),
        sa.Column("favored_positions_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_gm_draft_history_features_general_manager_id", "gm_draft_history_features", ["general_manager_id"])
    op.create_index("ix_gm_draft_history_features_draft_cycle_id", "gm_draft_history_features", ["draft_cycle_id"])

    op.create_table(
        "coach_draft_context_features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("head_coach_id", sa.Integer(), sa.ForeignKey("head_coaches.id"), nullable=False),
        sa.Column("draft_cycle_id", sa.Integer(), sa.ForeignKey("draft_cycles.id"), nullable=False),
        sa.Column("years_of_prior_history", sa.Integer(), nullable=False),
        sa.Column("offensive_background", sa.Boolean(), nullable=True),
        sa.Column("defensive_background", sa.Boolean(), nullable=True),
        sa.Column("prior_offense_pick_share", sa.Numeric(6, 4), nullable=True),
        sa.Column("prior_defense_pick_share", sa.Numeric(6, 4), nullable=True),
        sa.Column("prior_trenches_pick_share", sa.Numeric(6, 4), nullable=True),
        sa.Column("prior_skill_pick_share", sa.Numeric(6, 4), nullable=True),
        sa.Column("favored_positions_json", sa.Text(), nullable=True),
        sa.Column("scheme_bias_label", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_coach_draft_context_features_head_coach_id", "coach_draft_context_features", ["head_coach_id"])
    op.create_index("ix_coach_draft_context_features_draft_cycle_id", "coach_draft_context_features", ["draft_cycle_id"])

    op.create_table(
        "team_org_tendency_features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_cycle_id", sa.Integer(), sa.ForeignKey("draft_cycles.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("general_manager_id", sa.Integer(), sa.ForeignKey("general_managers.id"), nullable=True),
        sa.Column("head_coach_id", sa.Integer(), sa.ForeignKey("head_coaches.id"), nullable=True),
        sa.Column("organization_regime_key", sa.String(128), nullable=True),
        sa.Column("recent_offense_pick_share", sa.Numeric(6, 4), nullable=True),
        sa.Column("recent_defense_pick_share", sa.Numeric(6, 4), nullable=True),
        sa.Column("recent_trenches_pick_share", sa.Numeric(6, 4), nullable=True),
        sa.Column("recent_skill_pick_share", sa.Numeric(6, 4), nullable=True),
        sa.Column("recent_need_follow_rate", sa.Numeric(6, 4), nullable=True),
        sa.Column("recent_bpa_deviation_rate", sa.Numeric(6, 4), nullable=True),
        sa.Column("recent_early_round_positional_concentration", sa.Numeric(6, 4), nullable=True),
        sa.Column("recent_pick_volatility", sa.Numeric(6, 4), nullable=True),
        sa.Column("regime_stability_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_team_org_tendency_features_draft_cycle_id", "team_org_tendency_features", ["draft_cycle_id"])
    op.create_index("ix_team_org_tendency_features_team_id", "team_org_tendency_features", ["team_id"])

    op.create_table(
        "team_view_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_cycle_id", sa.Integer(), sa.ForeignKey("draft_cycles.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("overall_pick", sa.Integer(), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_team_view_predictions_draft_cycle_id", "team_view_predictions", ["draft_cycle_id"])
    op.create_index("ix_team_view_predictions_team_id", "team_view_predictions", ["team_id"])
    op.create_index("ix_team_view_predictions_overall_pick", "team_view_predictions", ["overall_pick"])
    op.create_index("ix_team_view_predictions_model_version", "team_view_predictions", ["model_version"])


def downgrade() -> None:
    op.drop_index("ix_team_view_predictions_model_version", table_name="team_view_predictions")
    op.drop_index("ix_team_view_predictions_overall_pick", table_name="team_view_predictions")
    op.drop_index("ix_team_view_predictions_team_id", table_name="team_view_predictions")
    op.drop_index("ix_team_view_predictions_draft_cycle_id", table_name="team_view_predictions")
    op.drop_table("team_view_predictions")

    op.drop_index("ix_team_org_tendency_features_team_id", table_name="team_org_tendency_features")
    op.drop_index("ix_team_org_tendency_features_draft_cycle_id", table_name="team_org_tendency_features")
    op.drop_table("team_org_tendency_features")

    op.drop_index("ix_coach_draft_context_features_draft_cycle_id", table_name="coach_draft_context_features")
    op.drop_index("ix_coach_draft_context_features_head_coach_id", table_name="coach_draft_context_features")
    op.drop_table("coach_draft_context_features")

    op.drop_index("ix_gm_draft_history_features_draft_cycle_id", table_name="gm_draft_history_features")
    op.drop_index("ix_gm_draft_history_features_general_manager_id", table_name="gm_draft_history_features")
    op.drop_table("gm_draft_history_features")

    op.drop_index("ix_team_front_office_history_team_id", table_name="team_front_office_history")
    op.drop_index("ix_team_front_office_history_draft_cycle_id", table_name="team_front_office_history")
    op.drop_table("team_front_office_history")

    op.drop_index("ix_head_coaches_normalized_name", table_name="head_coaches")
    op.drop_table("head_coaches")

    op.drop_index("ix_general_managers_normalized_name", table_name="general_managers")
    op.drop_table("general_managers")
