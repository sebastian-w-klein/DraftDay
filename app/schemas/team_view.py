from pydantic import BaseModel


class TeamViewOrgProfileResponse(BaseModel):
    team: str
    year: int
    gm_profile: dict[str, object] | None
    hc_profile: dict[str, object] | None
    regime_stability_score: float
    historical_tendency_metrics: dict[str, float]
    favored_positions_groups: dict[str, list[str]]


class TeamViewHistoryResponse(BaseModel):
    team: str
    year: int
    lookback_years: int
    recent_draft_history: list[dict[str, object]]
    early_round_picks: list[dict[str, object]]
    position_distributions: dict[str, int]
    need_alignment_summary: dict[str, float]


class TeamViewPositionProbsResponse(BaseModel):
    team: str
    year: int
    pick: int
    base_ml_position_probabilities: dict[str, float]
    org_adjusted_position_probabilities: dict[str, float]
    delta_by_position: dict[str, float]
    team_snapshot: dict[str, object]


class TeamViewPlayerCandidateInput(BaseModel):
    player_id: int | None = None
    player_name: str
    position: str
    prospect_score: float
    superstar_potential_score: float
    consensus_rank: int | None = None
    best_available_rank: int | None = None
    best_rank_in_position: int | None = None


class TeamViewPlayerProbsRequest(BaseModel):
    team: str
    year: int
    pick: int
    candidate_players: list[TeamViewPlayerCandidateInput] = []
    board_aware: bool = False


class TeamViewRankedPlayer(BaseModel):
    player_name: str
    position: str
    base_probability: float
    org_adjusted_probability: float
    need_component: float
    talent_component: float
    context_component: float
    organizational_component: float


class TeamViewPlayerProbsResponse(BaseModel):
    team: str
    year: int
    pick: int
    ranked_players: list[TeamViewRankedPlayer]
    integrated_explanation: str


class TeamViewSummaryResponse(BaseModel):
    team: str
    year: int
    pick: int
    team_snapshot: dict[str, object]
    org_summary: dict[str, object]
    consensus_top_players: list[dict[str, float | str]]
    ml_top_players: list[dict[str, float | str]]
    org_adjusted_top_players: list[dict[str, float | str]]
    top_position_predictions: dict[str, float]
    integrated_explanation: str


class TeamViewBacktestResponse(BaseModel):
    train_window: list[int]
    eval_window: list[int]
    comparison: dict[str, dict[str, float]]
