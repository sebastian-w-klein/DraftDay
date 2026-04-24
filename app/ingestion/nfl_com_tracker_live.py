"""Live draft picks from https://www.nfl.com/draft/tracker (embedded tracker payload in HTML)."""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.service import resolve_team_id
from app.models.entities import ActualDraftPick, DraftCycle, DraftOrderPick
from app.normalization.normalizers import normalize_player_name

NFL_DRAFT_TRACKER_URL = "https://www.nfl.com/draft/tracker"

_TEAM_UUID_ABBR_RE = re.compile(
    r'\\"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\\",\\"abbreviation\\":\\"([A-Z]{2,4})\\"'
)


@dataclass(frozen=True)
class NflTrackerPick:
    draft_year: int
    round_number: int
    pick_in_round: int
    overall_pick: int
    team_abbreviation: str
    player_display_name: str | None


def _parse_tracker_picks(html: str) -> list[NflTrackerPick]:
    """Parse dehydrated pick rows from NFL draft tracker HTML."""
    team_by_uuid = dict(_TEAM_UUID_ABBR_RE.findall(html))
    if not team_by_uuid:
        raise ValueError("NFL tracker HTML did not contain team abbreviation map")

    picks_start = html.find('\\"picks\\":[')
    if picks_start < 0:
        raise ValueError("NFL tracker HTML did not contain picks payload")
    picks_window_end = min(len(html), picks_start + 3_000_000)

    markers = [
        m
        for m in re.finditer(r'\\"overallPick\\":(\d+)', html)
        if picks_start <= m.start() < picks_window_end
    ]
    out: list[NflTrackerPick] = []
    for i, m in enumerate(markers):
        overall = int(m.group(1))
        next_start = markers[i + 1].start() if i + 1 < len(markers) else len(html)
        pre_start = max(0, m.start() - 500)
        pre = html[pre_start : m.start()]
        yi = pre.rfind('{\\"year\\"')
        if yi >= 0:
            obj_start = pre_start + yi
        else:
            yi2 = pre.rfind('[{\\"year\\"')
            if yi2 >= 0:
                obj_start = pre_start + yi2 + 1
            else:
                obj_start = m.start()
        b = html[obj_start:next_start]

        m_round = re.search(r'\\"round\\":(\d+)', b)
        m_pick = re.search(r'\\"pick\\":(\d+)', b)
        m_year = re.search(r'\\"year\\":(\d{4})', b)
        if not m_round or not m_pick or not m_year:
            continue
        round_number = int(m_round.group(1))
        pick_in_round = int(m_pick.group(1))
        year = int(m_year.group(1))

        tid_m = re.search(r'\\"teamId\\":\\"([0-9a-f-]{36})\\"', b)
        if not tid_m:
            continue
        abbr = team_by_uuid.get(tid_m.group(1))
        if not abbr:
            continue

        if '\\"prospect\\":null' in b[:2000]:
            player = None
        else:
            dm = re.search(r'\\"displayName\\":\\"((?:\\\\.|[^\\\\])*)\\"', b)
            if not dm:
                player = None
            else:
                raw = dm.group(1).replace("\\\\", "\\").replace('\\"', '"')
                if "\\" in raw:
                    player = raw.encode("utf-8", "surrogatepass").decode(
                        "unicode_escape", errors="surrogatepass"
                    )
                else:
                    player = raw

        out.append(
            NflTrackerPick(
                draft_year=year,
                round_number=round_number,
                pick_in_round=pick_in_round,
                overall_pick=overall,
                team_abbreviation=abbr,
                player_display_name=player,
            )
        )

    out.sort(key=lambda p: p.overall_pick)
    return out


def fetch_nfl_tracker_picks(timeout: float = 45.0) -> list[NflTrackerPick]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        r = client.get(NFL_DRAFT_TRACKER_URL)
        r.raise_for_status()
        html = r.text
    picks = _parse_tracker_picks(html)
    if not picks:
        raise ValueError("No picks parsed from NFL draft tracker (page format may have changed)")
    return picks


def ingest_nfl_com_tracker_picks(db: Session, draft_year: int) -> int:
    """
    Pull live / current tracker state from nfl.com and upsert ``actual_draft_picks``
    for the given draft year (must match embedded ``year`` on pick rows).

    Also upserts round-1 ``draft_order_picks`` (overall 1–32) from the same payload so
    upcoming slots reflect trades before a prospect is assigned.
    """
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == draft_year))
    if cycle is None:
        raise ValueError(f"Unknown draft year: {draft_year}")

    remote = fetch_nfl_tracker_picks()
    if remote[0].draft_year != draft_year:
        raise ValueError(
            f"Tracker feed is for {remote[0].draft_year}; requested draft_year={draft_year}. "
            "Adjust the draft year selector on the dashboard to match the live tracker."
        )

    updated = 0
    for p in remote:
        if not p.player_display_name:
            continue
        team_id = resolve_team_id(db, p.team_abbreviation)
        norm = normalize_player_name(p.player_display_name)
        row = db.scalar(
            select(ActualDraftPick).where(
                ActualDraftPick.draft_cycle_id == cycle.id,
                ActualDraftPick.overall_pick == p.overall_pick,
            )
        )
        if row is None:
            db.add(
                ActualDraftPick(
                    draft_cycle_id=cycle.id,
                    round_number=p.round_number,
                    overall_pick=p.overall_pick,
                    team_id=team_id,
                    player_id=None,
                    normalized_player_name=norm,
                )
            )
        else:
            row.round_number = p.round_number
            row.team_id = team_id
            row.normalized_player_name = norm
            row.player_id = None
        updated += 1

    order_source = "nfl.com-draft-tracker"
    for p in remote:
        if p.overall_pick > 32:
            continue
        team_id = resolve_team_id(db, p.team_abbreviation)
        order_row = db.scalar(
            select(DraftOrderPick).where(
                DraftOrderPick.draft_cycle_id == cycle.id,
                DraftOrderPick.overall_pick == p.overall_pick,
            )
        )
        if order_row is None:
            db.add(
                DraftOrderPick(
                    draft_cycle_id=cycle.id,
                    round_number=p.round_number,
                    overall_pick=p.overall_pick,
                    team_id=team_id,
                    source_name=order_source,
                )
            )
        else:
            order_row.round_number = p.round_number
            order_row.team_id = team_id
            order_row.source_name = order_source

    db.commit()
    return updated
