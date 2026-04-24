from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import DraftCycle, MockPick, TeamOrgTendencyFeature


@dataclass
class TeamHistoryRow:
    year: int
    overall_pick: int
    round_number: int
    position: str | None


def load_team_history(db: Session, team_id: int, year: int, lookback_years: int = 5) -> list[TeamHistoryRow]:
    cycles = db.scalars(
        select(DraftCycle).where(DraftCycle.year < year, DraftCycle.year >= (year - lookback_years))
    ).all()
    cycle_by_id = {c.id: c.year for c in cycles}
    rows = db.scalars(select(MockPick).where(MockPick.current_team_id == team_id, MockPick.draft_cycle_id.in_(cycle_by_id.keys()))).all()
    return [
        TeamHistoryRow(
            year=cycle_by_id[row.draft_cycle_id],
            overall_pick=row.overall_pick,
            round_number=row.round_number,
            position=row.normalized_position,
        )
        for row in sorted(rows, key=lambda r: (cycle_by_id[r.draft_cycle_id], r.overall_pick), reverse=True)
    ]


def load_org_tendency_row(db: Session, team_id: int, year: int) -> TeamOrgTendencyFeature | None:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if cycle is None:
        return None
    return db.scalar(
        select(TeamOrgTendencyFeature).where(
            TeamOrgTendencyFeature.team_id == team_id,
            TeamOrgTendencyFeature.draft_cycle_id == cycle.id,
        )
    )
