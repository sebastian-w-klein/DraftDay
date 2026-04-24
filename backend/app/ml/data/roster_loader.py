from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import DraftCycle, TeamRosterSnapshot


@dataclass
class RosterRow:
    team_id: int
    position: str
    snaps: int
    starts: int
    age: float | None
    experience_years: float | None
    starter_flag: bool | None
    injury_flag: bool | None


def load_roster_rows(db: Session, year: int) -> list[RosterRow]:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if cycle is None:
        return []
    rows = db.scalars(
        select(TeamRosterSnapshot).where(TeamRosterSnapshot.draft_cycle_id == cycle.id)
    ).all()
    return [
        RosterRow(
            team_id=row.team_id,
            position=row.position,
            snaps=row.snaps or 0,
            starts=row.games_started or 0,
            age=float(row.age) if row.age is not None else None,
            experience_years=float(row.experience_years) if row.experience_years is not None else None,
            starter_flag=row.starter_flag,
            injury_flag=row.injury_flag,
        )
        for row in rows
    ]
