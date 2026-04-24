"""Roster-based strength proxies to down-weight draft need when a room is already stocked."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import DraftCycle, TeamPositionNeedFeature
from backend.app.ml.data.roster_loader import RosterRow, load_roster_rows

# Approximate full-season snap ceilings for "room is set" (sum of roster at position).
_SNAP_CAPS: dict[str, int] = {
    "QB": 1100,
    "RB": 950,
    "WR": 2000,
    "TE": 850,
    "OT": 2200,
    "IOL": 2200,
    "EDGE": 1900,
    "DT": 1700,
    "LB": 1900,
    "CB": 1900,
    "S": 1600,
    "FB": 400,
    "K": 200,
    "P": 200,
    "LS": 200,
}


def _snap_cap(position: str) -> int:
    return _SNAP_CAPS.get(position.upper(), 1600)


def roster_strength_proxy(team_id: int, position: str, roster_rows: list[RosterRow]) -> float:
    """0 = weak/empty room, 1 = snaps near a full-season ceiling for that position group."""
    pos = position.upper()
    snaps = sum(r.snaps for r in roster_rows if r.team_id == team_id and r.position.upper() == pos)
    cap = _snap_cap(pos)
    if cap <= 0:
        return 0.0
    return max(0.0, min(1.0, float(snaps) / float(cap)))


def adjusted_overall_need(base: float, strength: float, *, dampen: float = 0.72) -> float:
    """Reduce displayed need when roster_strength is high (dampen in [0,1])."""
    if strength <= 0.0:
        return max(0.0, min(1.0, base))
    factor = max(0.08, 1.0 - dampen * strength)
    return max(0.04, min(0.99, base * factor))


def adjusted_need_map_for_team(db: Session, team_id: int, draft_year: int) -> dict[str, float]:
    """Map position -> roster-adjusted overall need (falls back to DB score when no roster data)."""
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == draft_year))
    if cycle is None:
        return {}
    rows = db.scalars(
        select(TeamPositionNeedFeature).where(
            TeamPositionNeedFeature.draft_cycle_id == cycle.id,
            TeamPositionNeedFeature.team_id == team_id,
        )
    ).all()
    roster = load_roster_rows(db, draft_year)
    out: dict[str, float] = {}
    for row in rows:
        base = float(row.overall_need_score or 0.0)
        if not roster:
            out[row.position] = base
            continue
        strength = roster_strength_proxy(team_id, row.position, roster)
        out[row.position] = adjusted_overall_need(base, strength)
    return out
