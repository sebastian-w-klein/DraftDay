from datetime import datetime

from pydantic import BaseModel


class ParsedPick(BaseModel):
    round_number: int
    overall_pick: int
    original_team: str | None
    current_team: str | None
    traded: bool = False
    player_name: str
    position: str | None = None
    school: str | None = None


class ParsedMockDraft(BaseModel):
    source_slug: str
    article_url: str
    title: str
    author_name: str | None
    published_at: datetime | None
    updated_at: datetime | None
    draft_year: int
    picks: list[ParsedPick]
