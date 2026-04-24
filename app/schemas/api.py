from datetime import datetime

from pydantic import BaseModel, Field


class PickProbability(BaseModel):
    player_name: str
    probability: float
    weighted_probability: float
    raw_probability: float | None = Field(
        default=None,
        description="Unsmoothed frequency among observed mock rows for this pick.",
    )
    raw_weighted_probability: float | None = Field(
        default=None,
        description="Unsmoothed recency-weighted share among observed mock rows.",
    )


class ConsensusConfidence(BaseModel):
    sample_size: int = Field(description="Number of mock pick rows aggregated for this pick.")
    unique_sources: int = Field(description="Distinct source_ids in the aggregation window.")
    unique_articles: int = Field(description="Distinct mock articles in the aggregation window.")
    smoothing_alpha: float = Field(description="Per-category Dirichlet prior mass (includes implicit OTHER bucket).")
    category_count: int = Field(description="Number of explicit categories (players) plus one OTHER bucket.")
    other_bucket_probability: float = Field(
        ge=0.0,
        le=1.0,
        description="Posterior mass on unseen players at this pick under the symmetric Dirichlet prior.",
    )
    low_confidence: bool = Field(
        description="Heuristic: thin multi-source coverage (e.g. few distinct sources or small sample)."
    )


class PickConsensusResponse(BaseModel):
    draft_year: int
    overall_pick: int
    top_players: list[PickProbability]
    updated_at: datetime
    consensus_confidence: ConsensusConfidence | None = None
    board_aware: bool = Field(
        default=False,
        description="When true, mock rows naming players already taken off the board were excluded.",
    )
    mock_rows_excluded: int | None = Field(
        default=None,
        description="Number of mock pick rows excluded due to board_aware filtering.",
    )


class PlayerLandingSpot(BaseModel):
    team: str
    probability: float
    raw_probability: float | None = None


class LandingConfidence(BaseModel):
    sample_size: int
    unique_teams: int
    unique_sources: int = Field(description="Distinct mock sources contributing at least one pick row.")
    unique_articles: int = Field(description="Distinct mock articles contributing at least one pick row.")
    smoothing_alpha: float
    category_count: int
    other_bucket_probability: float
    low_confidence: bool


class LiveDraftPickRow(BaseModel):
    overall_pick: int
    round_number: int
    team_abbreviation: str | None = None
    actual_player_name: str | None = Field(
        default=None,
        description="Normalized player key for the official pick (same space as consensus keys).",
    )
    consensus_top1_name: str | None = None
    consensus_top1_weighted_probability: float | None = None
    consensus_rank_of_actual: int | None = Field(
        default=None,
        description="1-based index in the consensus top list when the actual pick matches; "
        "0 when announced but not in the top-N list; null when no pick is announced yet.",
    )


class LiveDraftBoardResponse(BaseModel):
    draft_year: int
    source: str = "https://www.nfl.com/draft/tracker"
    synced_from_source: bool
    picks: list[LiveDraftPickRow]
    updated_at: datetime


class PlayerLandingSpotsResponse(BaseModel):
    draft_year: int
    player_name: str
    top_landing_spots: list[PlayerLandingSpot]
    updated_at: datetime
    landing_confidence: LandingConfidence | None = None
    resolved_lookup_name: str | None = Field(
        default=None,
        description="Canonical normalized player key used to match mock_picks rows.",
    )
    context_overall_pick: int | None = Field(
        default=None,
        description="When provided, mock_rows_at_context_pick counts all mocks at this slot (any player).",
    )
    mock_rows_at_context_pick: int | None = Field(
        default=None,
        description="Number of mock pick rows at context_overall_pick for the draft year (all players).",
    )
    draft_cycle_total_pick_rows: int | None = Field(
        default=None,
        description="All mock_picks rows for this draft year (any player).",
    )
    draft_cycle_mock_articles: int | None = Field(
        default=None,
        description="Distinct mock articles ingested for this draft year.",
    )
