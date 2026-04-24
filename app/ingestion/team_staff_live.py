import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import DraftCycle, GeneralManager, HeadCoach, Team, TeamFrontOfficeHistory
from app.normalization.normalizers import normalize_player_name

WIKI_API = "https://en.wikipedia.org/w/api.php"
PFR_TEAM_PAGE = "https://www.pro-football-reference.com/teams/{slug}/"

TEAM_WIKI_TITLES = {
    "ARI": "Arizona Cardinals",
    "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers",
    "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals",
    "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos",
    "DET": "Detroit Lions",
    "GB": "Green Bay Packers",
    "HOU": "Houston Texans",
    "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs",
    "LAC": "Los Angeles Chargers",
    "LAR": "Los Angeles Rams",
    "LV": "Las Vegas Raiders",
    "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings",
    "NE": "New England Patriots",
    "NO": "New Orleans Saints",
    "NYG": "New York Giants",
    "NYJ": "New York Jets",
    "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers",
    "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers",
    "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans",
    "WAS": "Washington Commanders",
}

TEAM_PFR_SLUGS = {
    "ARI": "crd",
    "ATL": "atl",
    "BAL": "rav",
    "BUF": "buf",
    "CAR": "car",
    "CHI": "chi",
    "CIN": "cin",
    "CLE": "cle",
    "DAL": "dal",
    "DEN": "den",
    "DET": "det",
    "GB": "gnb",
    "HOU": "htx",
    "IND": "clt",
    "JAX": "jax",
    "KC": "kan",
    "LAC": "sdg",
    "LAR": "ram",
    "LV": "rai",
    "MIA": "mia",
    "MIN": "min",
    "NE": "nwe",
    "NO": "nor",
    "NYG": "nyg",
    "NYJ": "nyj",
    "PHI": "phi",
    "PIT": "pit",
    "SEA": "sea",
    "SF": "sfo",
    "TB": "tam",
    "TEN": "oti",
    "WAS": "was",
}


def _extract_infobox_staff_from_html(html: str) -> tuple[str | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    infobox = soup.find("table", class_="infobox")
    if infobox is None:
        return None, None
    coach: str | None = None
    gm: str | None = None
    for row in infobox.find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if th is None or td is None:
            continue
        label = th.get_text(" ", strip=True).lower()
        value = td.get_text(" ", strip=True)
        if not value:
            continue
        if "general manager" in label and gm is None:
            gm = value
        elif ("head coach" in label or label == "coach") and coach is None:
            coach = value
    return coach, gm


def _extract_staff_from_pfr_html(html: str) -> tuple[str | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find(id="meta")
    if meta is None:
        return None, None
    coach = None
    gm = None
    text = meta.get_text(" ", strip=True)
    coach_match = re.search(r"Coach:\s*([A-Za-z.\-'\s]+)", text)
    gm_match = re.search(r"General Manager:\s*([A-Za-z.\-'\s]+)", text)
    if coach_match:
        coach = coach_match.group(1).strip()
    if gm_match:
        gm = gm_match.group(1).strip()
    return coach, gm
    return None


def _get_or_create_gm(db: Session, name: str) -> GeneralManager:
    normalized = normalize_player_name(name)
    row = db.scalar(select(GeneralManager).where(GeneralManager.normalized_name == normalized))
    if row is None:
        row = GeneralManager(full_name=name, normalized_name=normalized, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        db.add(row)
        db.flush()
    return row


def _get_or_create_hc(db: Session, name: str) -> HeadCoach:
    normalized = normalize_player_name(name)
    row = db.scalar(select(HeadCoach).where(HeadCoach.normalized_name == normalized))
    if row is None:
        row = HeadCoach(full_name=name, normalized_name=normalized, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        db.add(row)
        db.flush()
    return row


def ingest_live_team_staff(db: Session, draft_year: int) -> int:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == draft_year))
    if cycle is None:
        raise ValueError(f"Unknown draft year: {draft_year}")
    teams = db.scalars(select(Team).where(Team.active == True)).all()  # noqa: E712

    updated = 0
    with httpx.Client(
        timeout=20.0,
        follow_redirects=True,
        headers={
            "User-Agent": "DraftDayBot/1.0 (contact: local-dev)",
            "Accept": "application/json",
        },
    ) as client:
        for team in teams:
            title = TEAM_WIKI_TITLES.get(team.abbreviation)
            pfr_slug = TEAM_PFR_SLUGS.get(team.abbreviation)
            if not title:
                continue
            coach_name = None
            gm_name = None
            if pfr_slug:
                pfr_response = client.get(PFR_TEAM_PAGE.format(slug=pfr_slug))
                if pfr_response.status_code == 200:
                    coach_name, gm_name = _extract_staff_from_pfr_html(pfr_response.text)
            response = client.get(
                WIKI_API,
                params={
                    "action": "parse",
                    "page": title,
                    "prop": "text",
                    "format": "json",
                },
            )
            response.raise_for_status()
            parsed_html = response.json().get("parse", {}).get("text", {}).get("*", "")
            if not parsed_html:
                continue
            if not coach_name or not gm_name:
                wiki_coach, wiki_gm = _extract_infobox_staff_from_html(parsed_html)
                coach_name = coach_name or wiki_coach
                gm_name = gm_name or wiki_gm
            if not coach_name and not gm_name:
                continue

            gm = _get_or_create_gm(db, gm_name) if gm_name else None
            hc = _get_or_create_hc(db, coach_name) if coach_name else None
            office = db.scalar(
                select(TeamFrontOfficeHistory).where(
                    TeamFrontOfficeHistory.draft_cycle_id == cycle.id,
                    TeamFrontOfficeHistory.team_id == team.id,
                )
            )
            if office is None:
                office = TeamFrontOfficeHistory(
                    draft_cycle_id=cycle.id,
                    team_id=team.id,
                    general_manager_id=gm.id if gm else None,
                    head_coach_id=hc.id if hc else None,
                    gm_tenure_year=1,
                    hc_tenure_year=1,
                    control_regime_label="live-wikipedia",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(office)
            else:
                office.general_manager_id = gm.id if gm else office.general_manager_id
                office.head_coach_id = hc.id if hc else office.head_coach_id
                office.control_regime_label = "live-wikipedia"
                office.updated_at = datetime.utcnow()
            updated += 1

    db.commit()
    return updated
