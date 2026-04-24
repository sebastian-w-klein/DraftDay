from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import DraftCycle, DraftOrderPick, Team

TANKATHON_URL = "https://www.tankathon.com/nfl"

TEAM_SLUG_TO_ABBR = {
    "cardinals": "ARI",
    "falcons": "ATL",
    "ravens": "BAL",
    "bills": "BUF",
    "panthers": "CAR",
    "bears": "CHI",
    "bengals": "CIN",
    "browns": "CLE",
    "cowboys": "DAL",
    "broncos": "DEN",
    "lions": "DET",
    "packers": "GB",
    "texans": "HOU",
    "colts": "IND",
    "jaguars": "JAX",
    "chiefs": "KC",
    "chargers": "LAC",
    "rams": "LAR",
    "raiders": "LV",
    "dolphins": "MIA",
    "vikings": "MIN",
    "patriots": "NE",
    "saints": "NO",
    "giants": "NYG",
    "jets": "NYJ",
    "eagles": "PHI",
    "steelers": "PIT",
    "49ers": "SF",
    "seahawks": "SEA",
    "buccaneers": "TB",
    "titans": "TEN",
    "commanders": "WAS",
}


def ingest_live_tankathon_draft_order(db: Session, draft_year: int) -> int:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == draft_year))
    if cycle is None:
        raise ValueError(f"Unknown draft year: {draft_year}")

    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        response = client.get(TANKATHON_URL)
        response.raise_for_status()
        html = response.text
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="draft-board")
    if table is None:
        raise ValueError("Unable to parse live draft order table")

    upserts = 0
    rows = table.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        pick_text = cells[0].get_text(strip=True)
        if not pick_text.isdigit():
            continue
        overall_pick = int(pick_text)
        team_link = cells[1].find("a")
        if team_link is None:
            continue
        href = str(team_link.get("href") or "")
        slug = href.split("/")[-1].strip().lower()
        abbr = TEAM_SLUG_TO_ABBR.get(slug)
        if abbr is None:
            continue
        team = db.scalar(select(Team).where(Team.abbreviation == abbr))
        if team is None:
            continue
        existing = db.scalar(
            select(DraftOrderPick).where(
                DraftOrderPick.draft_cycle_id == cycle.id,
                DraftOrderPick.overall_pick == overall_pick,
            )
        )
        if existing is None:
            db.add(
                DraftOrderPick(
                    draft_cycle_id=cycle.id,
                    round_number=1,
                    overall_pick=overall_pick,
                    team_id=team.id,
                    source_name=f"tankathon-live-{datetime.utcnow().date().isoformat()}",
                )
            )
        else:
            existing.team_id = team.id
            existing.round_number = 1
            existing.source_name = f"tankathon-live-{datetime.utcnow().date().isoformat()}"
        upserts += 1

    db.commit()
    return upserts
