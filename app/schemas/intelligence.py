from pydantic import BaseModel


class PositionNeedItem(BaseModel):
    position: str
    short_term_need_score: float
    long_term_need_score: float
    overall_need_score: float
    feature_summary: dict[str, float]


class TeamNeedsResponse(BaseModel):
    team: str
    year: int
    needs: list[PositionNeedItem]
    top_need_positions: list[str]
    feature_summary: list[PositionNeedItem]


class PositionProbabilityResponse(BaseModel):
    team: str
    year: int
    overall_pick: int
    model_version: str
    position_probabilities: dict[str, float]
    need_profile: list[dict[str, float | str | int]]
    explanation_summary: dict[str, float | str | int]


class PickPlayerCandidateInput(BaseModel):
    player_id: int | None = None
    player_name: str
    position: str
    prospect_score: float
    superstar_potential_score: float
    consensus_rank: int | None = None
    best_available_rank: int | None = None
    best_rank_in_position: int | None = None


class PickPlayerProbsRequest(BaseModel):
    team: str
    pick: int
    year: int
    candidate_players: list[PickPlayerCandidateInput] = []
    board_aware: bool = False


class RankedPlayerProbability(BaseModel):
    player_name: str
    position: str
    probability: float
    need_component: float
    talent_component: float
    context_component: float
    superstar_override_score: float


class PickPlayerProbsResponse(BaseModel):
    team: str
    pick: int
    year: int
    model_version: str
    ranked_players: list[RankedPlayerProbability]
    explanation_summary: dict[str, float | str | int]


class ConsensusVsMlResponse(BaseModel):
    team: str
    pick: int
    year: int
    consensus_top_players: list[dict[str, float | str]]
    ml_top_players: list[dict[str, float | str]]
    overlap: list[str]
    disagreement_score: float
    divergence_explanation: dict[str, float | str | int]


class ModelMetadataResponse(BaseModel):
    model_family: str
    model_version: str
    train_window: list[int]
    validation_window: list[int | None]
    test_window: list[int | None]
    metrics: dict[str, float | int | str]
    feature_groups: list[str]
    training_timestamp: str


class IntelligenceModelMetadataResponse(BaseModel):
    models: list[ModelMetadataResponse]
