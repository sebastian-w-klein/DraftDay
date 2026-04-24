import re
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.ingestion.service import upsert_mock_draft  # noqa: E402
from app.models.entities import (  # noqa: E402
    DraftCycle,
    DraftOrderPick,
    MockArticle,
    MockPick,
    ParserType,
    Source,
    SourceType,
    Team,
)
from app.schemas.parsed import ParsedMockDraft, ParsedPick  # noqa: E402

MOCK_URL = "https://www.tankathon.com/nfl/mock_draft"
SOURCE_SLUG = "tankathon-live-mock"

POS_PATTERN = re.compile(
    r"^(?P<name>.+?)(?P<pos>QB|RB|WR|TE|OT|IOL|C|G|EDGE|DT|LB|CB|S|K|P)(?:/[A-Z]+)?\s*\|\s*(?P<school>.+)$"
)


def _ensure_source(db) -> Source:
    source = db.scalar(select(Source).where(Source.slug == SOURCE_SLUG))
    if source is None:
        source = Source(
            slug=SOURCE_SLUG,
            name="Tankathon Live Mock",
            base_url="https://www.tankathon.com",
            source_type=SourceType.aggregator,
            parser_type=ParserType.manual_upload,
            allowed_for_automation=True,
            paywalled=False,
            default_weight=Decimal("1.10"),
            recency_half_life_days=7,
            active=True,
        )
        db.add(source)
        db.flush()
    return source


def main() -> None:
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.utcnow().year
    with SessionLocal() as db:
        cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
        if cycle is None:
            print(f"Draft cycle {year} not found.")
            return

        _ensure_source(db)
        db.query(MockPick).filter(
            MockPick.draft_cycle_id == cycle.id,
            MockPick.source_id == select(Source.id).where(Source.slug == SOURCE_SLUG).scalar_subquery(),
        ).delete(synchronize_session=False)
        db.query(MockArticle).filter(
            MockArticle.draft_cycle_id == cycle.id,
            MockArticle.article_url == MOCK_URL,
        ).delete(synchronize_session=False)
        db.commit()

        pick_team_rows = db.execute(
            select(DraftOrderPick.overall_pick, Team.abbreviation)
            .join(Team, Team.id == DraftOrderPick.team_id)
            .where(DraftOrderPick.draft_cycle_id == cycle.id, DraftOrderPick.round_number == 1)
            .order_by(DraftOrderPick.overall_pick.asc())
        ).all()
        pick_to_team = {int(overall): str(abbr) for overall, abbr in pick_team_rows}
        if len(pick_to_team) < 32:
            print("Draft order missing rows; run live draft-order ingestion first.")
            return

        html = httpx.get(MOCK_URL, timeout=20).text
        soup = BeautifulSoup(html, "html.parser")
        player_links = []
        seen = set()
        for a in soup.find_all("a", href=True):
            if "/nfl/players/" not in str(a.get("href")):
                continue
            text = a.get_text(" ", strip=True)
            match = POS_PATTERN.match(text)
            if not match:
                continue
            name = match.group("name").strip()
            pos = match.group("pos").strip()
            school = match.group("school").strip()
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            player_links.append((name, pos, school))
            if len(player_links) >= 32:
                break
        if len(player_links) < 32:
            print("Failed to parse 32 round-1 players from live mock board.")
            return

        parsed = ParsedMockDraft(
            source_slug=SOURCE_SLUG,
            article_url=MOCK_URL,
            title=f"Tankathon Live Mock {year}",
            author_name="Tankathon",
            published_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            draft_year=year,
            picks=[
                ParsedPick(
                    round_number=1,
                    overall_pick=idx + 1,
                    original_team=pick_to_team[idx + 1],
                    current_team=pick_to_team[idx + 1],
                    traded=False,
                    player_name=row[0],
                    position=row[1],
                    school=row[2],
                )
                for idx, row in enumerate(player_links)
            ],
        )
        upsert_mock_draft(db, parsed)
    print(f"Ingested live round-1 mock picks for {year}.")


if __name__ == "__main__":
    main()
