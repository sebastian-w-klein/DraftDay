import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import DraftCycle, ProspectFeature
from app.normalization.normalizers import normalize_player_name

TANKATHON_MOCK_URL = "https://www.tankathon.com/nfl/mock_draft"

POS_PATTERN = re.compile(
    r"^(?P<name>.+?)(?P<pos>QB|RB|WR|TE|OT|IOL|C|G|EDGE|DT|LB|CB|S|K|P)(?:/[A-Z]+)?\s*\|\s*(?P<school>.+)$"
)


def ingest_live_tankathon_prospects(db: Session, draft_year: int, limit: int = 128) -> int:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == draft_year))
    if cycle is None:
        raise ValueError(f"Unknown draft year: {draft_year}")

    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        response = client.get(TANKATHON_MOCK_URL)
        response.raise_for_status()
        html = response.text
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.find_all("a", href=True)

    seen: set[str] = set()
    candidates: list[tuple[str, str, str]] = []
    for a in anchors:
        href = str(a.get("href"))
        if "/nfl/players/" not in href:
            continue
        text = a.get_text(" ", strip=True)
        match = POS_PATTERN.match(text)
        if not match:
            continue
        name = match.group("name").strip()
        position = match.group("pos").strip()
        school = match.group("school").strip()
        key = normalize_player_name(name)
        if not key or key in seen:
            continue
        seen.add(key)
        candidates.append((name, position, school))
        if len(candidates) >= limit:
            break

    if not candidates:
        raise ValueError("No prospects parsed from live source")

    db.query(ProspectFeature).filter(ProspectFeature.draft_cycle_id == cycle.id).delete()
    for idx, (name, position, school) in enumerate(candidates, start=1):
        score = max(0.1, 1.0 - (idx / (len(candidates) + 8)))
        db.add(
            ProspectFeature(
                draft_cycle_id=cycle.id,
                player_id=None,
                full_name=name,
                normalized_name=normalize_player_name(name),
                position=position,
                school=school,
                age=None,
                height=None,
                weight=None,
                athletic_score=score,
                production_score=score,
                consensus_rank=idx,
                big_board_rank=idx,
                positional_rank=1,
                market_score=score,
                superstar_potential_score=max(0.1, score * 0.95),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        )
    db.commit()
    return len(candidates)
