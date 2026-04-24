import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SourceType(str, enum.Enum):
    expert = "expert"
    community = "community"
    simulator = "simulator"
    aggregator = "aggregator"
    manual = "manual"


class ParserType(str, enum.Enum):
    html_static = "html_static"
    html_dynamic = "html_dynamic"
    rss = "rss"
    manual_upload = "manual_upload"


class ParseStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
    partial = "partial"


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    base_url: Mapped[str] = mapped_column(String(1024))
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType, name="source_type"))
    parser_type: Mapped[ParserType] = mapped_column(Enum(ParserType, name="parser_type"))
    allowed_for_automation: Mapped[bool] = mapped_column(Boolean, default=False)
    paywalled: Mapped[bool] = mapped_column(Boolean, default=False)
    default_weight: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=1.0)
    recency_half_life_days: Mapped[int] = mapped_column(Integer, default=14)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Author(Base):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), index=True)
    historical_accuracy_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DraftCycle(Base):
    __tablename__ = "draft_cycles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    start_date: Mapped[date] = mapped_column(Date)
    draft_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    abbreviation: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), unique=True)
    city: Mapped[str] = mapped_column(String(100))
    conference: Mapped[str | None] = mapped_column(String(20), nullable=True)
    division: Mapped[str | None] = mapped_column(String(20), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    normalized_name: Mapped[str] = mapped_column(String(255), index=True)
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    position: Mapped[str] = mapped_column(String(10))
    school: Mapped[str] = mapped_column(String(255))
    school_normalized: Mapped[str] = mapped_column(String(255))
    class_year: Mapped[str | None] = mapped_column(String(32), nullable=True)
    big_board_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_draft_year: Mapped[int] = mapped_column(Integer, index=True)


class MockArticle(Base):
    __tablename__ = "mock_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("authors.id"), nullable=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    article_url: Mapped[str] = mapped_column(String(1024))
    canonical_url: Mapped[str] = mapped_column(String(1024))
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    content_hash: Mapped[str] = mapped_column(String(128), index=True)
    raw_html_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    parser_version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    parse_status: Mapped[ParseStatus] = mapped_column(
        Enum(ParseStatus, name="parse_status"), default=ParseStatus.pending
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    versions: Mapped[list["MockVersion"]] = relationship(back_populates="mock_article")


class MockVersion(Base):
    __tablename__ = "mock_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mock_article_id: Mapped[int] = mapped_column(ForeignKey("mock_articles.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    content_hash: Mapped[str] = mapped_column(String(128), index=True)
    raw_html_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    parse_status: Mapped[ParseStatus] = mapped_column(
        Enum(ParseStatus, name="parse_status_version"), default=ParseStatus.pending
    )
    mock_article: Mapped[MockArticle] = relationship(back_populates="versions")


class MockPick(Base):
    __tablename__ = "mock_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mock_article_id: Mapped[int] = mapped_column(ForeignKey("mock_articles.id"), index=True)
    mock_version_id: Mapped[int | None] = mapped_column(ForeignKey("mock_versions.id"), nullable=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("authors.id"), nullable=True)
    round_number: Mapped[int] = mapped_column(Integer)
    overall_pick: Mapped[int] = mapped_column(Integer, index=True)
    original_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    current_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    traded: Mapped[bool] = mapped_column(Boolean, default=False)
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    raw_player_name: Mapped[str] = mapped_column(String(255))
    normalized_player_name: Mapped[str] = mapped_column(String(255), index=True)
    raw_position: Mapped[str | None] = mapped_column(String(16), nullable=True)
    normalized_position: Mapped[str | None] = mapped_column(String(16), nullable=True)
    raw_school: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_school: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence_extraction: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SourceAccuracy(Base):
    __tablename__ = "source_accuracy"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("authors.id"), nullable=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    exact_pick_hits: Mapped[int] = mapped_column(Integer, default=0)
    player_team_hits: Mapped[int] = mapped_column(Integer, default=0)
    round1_player_hits: Mapped[int] = mapped_column(Integer, default=0)
    avg_pick_distance: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    weighted_accuracy_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ManualOverride(Base):
    __tablename__ = "manual_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    field_name: Mapped[str] = mapped_column(String(64))
    old_value: Mapped[str] = mapped_column(Text)
    new_value: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(50), index=True)
    items_discovered: Mapped[int] = mapped_column(Integer, default=0)
    items_fetched: Mapped[int] = mapped_column(Integer, default=0)
    items_parsed: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
    logs_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class PlayerAlias(Base):
    __tablename__ = "player_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alias_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    normalized_name: Mapped[str] = mapped_column(String(255), index=True)


class SchoolAlias(Base):
    __tablename__ = "school_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    alias_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    normalized_school: Mapped[str] = mapped_column(String(255), index=True)


class ActualDraftPick(Base):
    __tablename__ = "actual_draft_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    round_number: Mapped[int] = mapped_column(Integer)
    overall_pick: Mapped[int] = mapped_column(Integer, index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    normalized_player_name: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TeamRosterSnapshot(Base):
    __tablename__ = "team_roster_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    player_name: Mapped[str] = mapped_column(String(255))
    normalized_player_name: Mapped[str] = mapped_column(String(255), index=True)
    position: Mapped[str] = mapped_column(String(16), index=True)
    age: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    experience_years: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    games_played: Mapped[int | None] = mapped_column(Integer, nullable=True)
    games_started: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snaps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    under_contract: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    starter_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    injury_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TeamPositionNeedFeature(Base):
    __tablename__ = "team_position_need_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    position: Mapped[str] = mapped_column(String(16), index=True)
    returning_snaps: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    returning_starts: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    avg_age: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    avg_experience: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    depth_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    starter_continuity: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    recent_draft_investment: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    recent_free_agent_investment: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    short_term_need_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    long_term_need_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    overall_need_score: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProspectFeature(Base):
    __tablename__ = "prospect_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    normalized_name: Mapped[str] = mapped_column(String(255), index=True)
    position: Mapped[str] = mapped_column(String(16), index=True)
    school: Mapped[str] = mapped_column(String(255))
    age: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    height: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    weight: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    athletic_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    production_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    consensus_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    big_board_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    positional_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    superstar_potential_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PickContextFeature(Base):
    __tablename__ = "pick_context_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    overall_pick: Mapped[int] = mapped_column(Integer, index=True)
    round_number: Mapped[int] = mapped_column(Integer)
    prior_season_wins: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    playoff_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    roster_strength_proxy: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    number_of_total_picks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top_need_position: Mapped[str | None] = mapped_column(String(16), nullable=True)
    best_available_player_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    best_available_position: Mapped[str | None] = mapped_column(String(16), nullable=True)
    board_scarcity_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CandidatePlayerFeature(Base):
    __tablename__ = "candidate_player_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    overall_pick: Mapped[int] = mapped_column(Integer, index=True)
    round_number: Mapped[int] = mapped_column(Integer)
    candidate_player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    candidate_player_name: Mapped[str] = mapped_column(String(255))
    position: Mapped[str] = mapped_column(String(16), index=True)
    available_at_pick: Mapped[bool] = mapped_column(Boolean, default=True)
    team_need_score: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0)
    prospect_score: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0)
    superstar_potential_score: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0)
    positional_scarcity_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    consensus_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rank_gap_from_best_available: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    rank_gap_within_position: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    selected_label: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MlModelRun(Base):
    __tablename__ = "ml_model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_family: Mapped[str] = mapped_column(String(64), index=True)
    model_version: Mapped[str] = mapped_column(String(64), index=True)
    train_year_start: Mapped[int] = mapped_column(Integer)
    train_year_end: Mapped[int] = mapped_column(Integer)
    validation_year_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validation_year_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    test_year_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    test_year_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metrics_json: Mapped[str] = mapped_column(Text)
    artifact_path: Mapped[str] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MlPrediction(Base):
    __tablename__ = "ml_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    overall_pick: Mapped[int] = mapped_column(Integer, index=True)
    model_version: Mapped[str] = mapped_column(String(64), index=True)
    prediction_type: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GeneralManager(Base):
    __tablename__ = "general_managers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    normalized_name: Mapped[str] = mapped_column(String(255), index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HeadCoach(Base):
    __tablename__ = "head_coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    normalized_name: Mapped[str] = mapped_column(String(255), index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TeamFrontOfficeHistory(Base):
    __tablename__ = "team_front_office_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    general_manager_id: Mapped[int | None] = mapped_column(ForeignKey("general_managers.id"), nullable=True)
    head_coach_id: Mapped[int | None] = mapped_column(ForeignKey("head_coaches.id"), nullable=True)
    gm_tenure_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hc_tenure_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    control_regime_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GmDraftHistoryFeature(Base):
    __tablename__ = "gm_draft_history_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    general_manager_id: Mapped[int] = mapped_column(ForeignKey("general_managers.id"), index=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    years_of_prior_draft_history: Mapped[int] = mapped_column(Integer, default=0)
    total_prior_picks: Mapped[int] = mapped_column(Integer, default=0)
    avg_pick_value_spent_offense: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    avg_pick_value_spent_defense: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    pct_first_round_trenches: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    pct_first_round_skill: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    pct_picks_same_side_as_top_need: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    pct_picks_best_player_available_proxy: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    pct_early_round_trades_up: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    pct_early_round_trades_down: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    avg_positional_value_of_picks: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    favored_positions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CoachDraftContextFeature(Base):
    __tablename__ = "coach_draft_context_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    head_coach_id: Mapped[int] = mapped_column(ForeignKey("head_coaches.id"), index=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    years_of_prior_history: Mapped[int] = mapped_column(Integer, default=0)
    offensive_background: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    defensive_background: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    prior_offense_pick_share: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    prior_defense_pick_share: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    prior_trenches_pick_share: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    prior_skill_pick_share: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    favored_positions_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheme_bias_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TeamOrgTendencyFeature(Base):
    __tablename__ = "team_org_tendency_features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    general_manager_id: Mapped[int | None] = mapped_column(ForeignKey("general_managers.id"), nullable=True)
    head_coach_id: Mapped[int | None] = mapped_column(ForeignKey("head_coaches.id"), nullable=True)
    organization_regime_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recent_offense_pick_share: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    recent_defense_pick_share: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    recent_trenches_pick_share: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    recent_skill_pick_share: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    recent_need_follow_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    recent_bpa_deviation_rate: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    recent_early_round_positional_concentration: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4), nullable=True
    )
    recent_pick_volatility: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    regime_stability_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TeamViewPrediction(Base):
    __tablename__ = "team_view_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    overall_pick: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    model_version: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DraftOrderPick(Base):
    __tablename__ = "draft_order_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_cycle_id: Mapped[int] = mapped_column(ForeignKey("draft_cycles.id"), index=True)
    round_number: Mapped[int] = mapped_column(Integer, index=True)
    overall_pick: Mapped[int] = mapped_column(Integer, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    source_name: Mapped[str] = mapped_column(String(128), default="manual-draft-order")
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HistoricalIngestBatch(Base):
    """Tracks bulk historical ETL runs (outcomes, mocks, rosters, boards) for audit and replays."""

    __tablename__ = "historical_ingest_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_family: Mapped[str] = mapped_column(String(64), index=True)
    source_key: Mapped[str] = mapped_column(String(128), index=True)
    year_start: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    year_end: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0)
    rows_failed: Mapped[int] = mapped_column(Integer, default=0)
    artifact_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
