from datetime import datetime

from pydantic import BaseModel, HttpUrl

from app.schemas.parsed import ParsedPick


class ManualMockDraftRequest(BaseModel):
    source_slug: str
    article_url: HttpUrl | None = None
    title: str
    author_name: str | None = None
    published_at: datetime | None = None
    updated_at: datetime | None = None
    draft_year: int
    picks: list[ParsedPick]


class IngestionResponse(BaseModel):
    article_id: int
    status: str
    picks_inserted: int


class ParseFromUrlRequest(BaseModel):
    source_slug: str
    url: HttpUrl


class ActualPickInput(BaseModel):
    draft_year: int
    round_number: int
    overall_pick: int
    player_name: str
    team_abbreviation: str | None = None


class BacktestResult(BaseModel):
    source_slug: str
    exact_pick_hits: int
    player_team_hits: int
    round1_player_hits: int
    avg_pick_distance: float
    weighted_accuracy_score: float


class DraftOrderPickInput(BaseModel):
    overall_pick: int
    round_number: int = 1
    team_abbreviation: str


class DraftOrderIngestionRequest(BaseModel):
    draft_year: int
    source_name: str = "manual-draft-order"
    picks: list[DraftOrderPickInput]
