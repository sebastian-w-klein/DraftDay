"""add draft intelligence tables

Revision ID: 0003_draft_intelligence_tables
Revises: 0002_actual_picks
Create Date: 2026-04-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_draft_intelligence_tables"
down_revision: str | None = "0002_actual_picks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "team_roster_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_cycle_id", sa.Integer(), sa.ForeignKey("draft_cycles.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("player_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_player_name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.String(length=16), nullable=False),
        sa.Column("age", sa.Numeric(5, 2), nullable=True),
        sa.Column("experience_years", sa.Numeric(5, 2), nullable=True),
        sa.Column("games_played", sa.Integer(), nullable=True),
        sa.Column("games_started", sa.Integer(), nullable=True),
        sa.Column("snaps", sa.Integer(), nullable=True),
        sa.Column("under_contract", sa.Boolean(), nullable=True),
        sa.Column("starter_flag", sa.Boolean(), nullable=True),
        sa.Column("injury_flag", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_team_roster_snapshots_draft_cycle_id", "team_roster_snapshots", ["draft_cycle_id"])
    op.create_index("ix_team_roster_snapshots_team_id", "team_roster_snapshots", ["team_id"])
    op.create_index(
        "ix_team_roster_snapshots_normalized_player_name",
        "team_roster_snapshots",
        ["normalized_player_name"],
    )
    op.create_index("ix_team_roster_snapshots_position", "team_roster_snapshots", ["position"])

    op.create_table(
        "team_position_need_features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_cycle_id", sa.Integer(), sa.ForeignKey("draft_cycles.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("position", sa.String(length=16), nullable=False),
        sa.Column("returning_snaps", sa.Numeric(10, 2), nullable=True),
        sa.Column("returning_starts", sa.Numeric(10, 2), nullable=True),
        sa.Column("avg_age", sa.Numeric(5, 2), nullable=True),
        sa.Column("avg_experience", sa.Numeric(5, 2), nullable=True),
        sa.Column("depth_count", sa.Integer(), nullable=True),
        sa.Column("starter_continuity", sa.Numeric(6, 4), nullable=True),
        sa.Column("recent_draft_investment", sa.Numeric(6, 4), nullable=True),
        sa.Column("recent_free_agent_investment", sa.Numeric(6, 4), nullable=True),
        sa.Column("short_term_need_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("long_term_need_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("overall_need_score", sa.Numeric(6, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_team_position_need_features_draft_cycle_id", "team_position_need_features", ["draft_cycle_id"]
    )
    op.create_index("ix_team_position_need_features_team_id", "team_position_need_features", ["team_id"])
    op.create_index("ix_team_position_need_features_position", "team_position_need_features", ["position"])

    op.create_table(
        "prospect_features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_cycle_id", sa.Integer(), sa.ForeignKey("draft_cycles.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.String(length=16), nullable=False),
        sa.Column("school", sa.String(length=255), nullable=False),
        sa.Column("age", sa.Numeric(5, 2), nullable=True),
        sa.Column("height", sa.Numeric(6, 2), nullable=True),
        sa.Column("weight", sa.Numeric(6, 2), nullable=True),
        sa.Column("athletic_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("production_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("consensus_rank", sa.Integer(), nullable=True),
        sa.Column("big_board_rank", sa.Integer(), nullable=True),
        sa.Column("positional_rank", sa.Integer(), nullable=True),
        sa.Column("market_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("superstar_potential_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_prospect_features_draft_cycle_id", "prospect_features", ["draft_cycle_id"])
    op.create_index("ix_prospect_features_normalized_name", "prospect_features", ["normalized_name"])
    op.create_index("ix_prospect_features_position", "prospect_features", ["position"])

    op.create_table(
        "pick_context_features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_cycle_id", sa.Integer(), sa.ForeignKey("draft_cycles.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("overall_pick", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("prior_season_wins", sa.Numeric(5, 2), nullable=True),
        sa.Column("playoff_flag", sa.Boolean(), nullable=True),
        sa.Column("roster_strength_proxy", sa.Numeric(6, 4), nullable=True),
        sa.Column("number_of_total_picks", sa.Integer(), nullable=True),
        sa.Column("top_need_position", sa.String(length=16), nullable=True),
        sa.Column("best_available_player_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("best_available_position", sa.String(length=16), nullable=True),
        sa.Column("board_scarcity_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_pick_context_features_draft_cycle_id", "pick_context_features", ["draft_cycle_id"])
    op.create_index("ix_pick_context_features_team_id", "pick_context_features", ["team_id"])
    op.create_index("ix_pick_context_features_overall_pick", "pick_context_features", ["overall_pick"])

    op.create_table(
        "candidate_player_features",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_cycle_id", sa.Integer(), sa.ForeignKey("draft_cycles.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("overall_pick", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("candidate_player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=True),
        sa.Column("candidate_player_name", sa.String(length=255), nullable=False),
        sa.Column("position", sa.String(length=16), nullable=False),
        sa.Column("available_at_pick", sa.Boolean(), nullable=False),
        sa.Column("team_need_score", sa.Numeric(6, 4), nullable=False),
        sa.Column("prospect_score", sa.Numeric(6, 4), nullable=False),
        sa.Column("superstar_potential_score", sa.Numeric(6, 4), nullable=False),
        sa.Column("positional_scarcity_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("consensus_rank", sa.Integer(), nullable=True),
        sa.Column("rank_gap_from_best_available", sa.Numeric(6, 4), nullable=True),
        sa.Column("rank_gap_within_position", sa.Numeric(6, 4), nullable=True),
        sa.Column("selected_label", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_candidate_player_features_draft_cycle_id",
        "candidate_player_features",
        ["draft_cycle_id"],
    )
    op.create_index("ix_candidate_player_features_team_id", "candidate_player_features", ["team_id"])
    op.create_index(
        "ix_candidate_player_features_overall_pick", "candidate_player_features", ["overall_pick"]
    )
    op.create_index("ix_candidate_player_features_position", "candidate_player_features", ["position"])

    op.create_table(
        "ml_model_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_family", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("train_year_start", sa.Integer(), nullable=False),
        sa.Column("train_year_end", sa.Integer(), nullable=False),
        sa.Column("validation_year_start", sa.Integer(), nullable=True),
        sa.Column("validation_year_end", sa.Integer(), nullable=True),
        sa.Column("test_year_start", sa.Integer(), nullable=True),
        sa.Column("test_year_end", sa.Integer(), nullable=True),
        sa.Column("metrics_json", sa.Text(), nullable=False),
        sa.Column("artifact_path", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ml_model_runs_model_family", "ml_model_runs", ["model_family"])
    op.create_index("ix_ml_model_runs_model_version", "ml_model_runs", ["model_version"])

    op.create_table(
        "ml_predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_cycle_id", sa.Integer(), sa.ForeignKey("draft_cycles.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("overall_pick", sa.Integer(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("prediction_type", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ml_predictions_draft_cycle_id", "ml_predictions", ["draft_cycle_id"])
    op.create_index("ix_ml_predictions_team_id", "ml_predictions", ["team_id"])
    op.create_index("ix_ml_predictions_overall_pick", "ml_predictions", ["overall_pick"])
    op.create_index("ix_ml_predictions_model_version", "ml_predictions", ["model_version"])
    op.create_index("ix_ml_predictions_prediction_type", "ml_predictions", ["prediction_type"])


def downgrade() -> None:
    op.drop_index("ix_ml_predictions_prediction_type", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_model_version", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_overall_pick", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_team_id", table_name="ml_predictions")
    op.drop_index("ix_ml_predictions_draft_cycle_id", table_name="ml_predictions")
    op.drop_table("ml_predictions")

    op.drop_index("ix_ml_model_runs_model_version", table_name="ml_model_runs")
    op.drop_index("ix_ml_model_runs_model_family", table_name="ml_model_runs")
    op.drop_table("ml_model_runs")

    op.drop_index("ix_candidate_player_features_position", table_name="candidate_player_features")
    op.drop_index("ix_candidate_player_features_overall_pick", table_name="candidate_player_features")
    op.drop_index("ix_candidate_player_features_team_id", table_name="candidate_player_features")
    op.drop_index("ix_candidate_player_features_draft_cycle_id", table_name="candidate_player_features")
    op.drop_table("candidate_player_features")

    op.drop_index("ix_pick_context_features_overall_pick", table_name="pick_context_features")
    op.drop_index("ix_pick_context_features_team_id", table_name="pick_context_features")
    op.drop_index("ix_pick_context_features_draft_cycle_id", table_name="pick_context_features")
    op.drop_table("pick_context_features")

    op.drop_index("ix_prospect_features_position", table_name="prospect_features")
    op.drop_index("ix_prospect_features_normalized_name", table_name="prospect_features")
    op.drop_index("ix_prospect_features_draft_cycle_id", table_name="prospect_features")
    op.drop_table("prospect_features")

    op.drop_index("ix_team_position_need_features_position", table_name="team_position_need_features")
    op.drop_index("ix_team_position_need_features_team_id", table_name="team_position_need_features")
    op.drop_index(
        "ix_team_position_need_features_draft_cycle_id", table_name="team_position_need_features"
    )
    op.drop_table("team_position_need_features")

    op.drop_index("ix_team_roster_snapshots_position", table_name="team_roster_snapshots")
    op.drop_index(
        "ix_team_roster_snapshots_normalized_player_name", table_name="team_roster_snapshots"
    )
    op.drop_index("ix_team_roster_snapshots_team_id", table_name="team_roster_snapshots")
    op.drop_index("ix_team_roster_snapshots_draft_cycle_id", table_name="team_roster_snapshots")
    op.drop_table("team_roster_snapshots")
