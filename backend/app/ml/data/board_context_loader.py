from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import DraftCycle, PickContextFeature


@dataclass
class BoardContextRow:
    team_id: int
    overall_pick: int
    round_number: int
    board_scarcity_score: float
    best_available_player_score: float
    top_need_position: str | None


def load_board_context_rows(db: Session, year: int) -> list[BoardContextRow]:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if cycle is None:
        return []
    rows = db.scalars(select(PickContextFeature).where(PickContextFeature.draft_cycle_id == cycle.id)).all()
    return [
        BoardContextRow(
            team_id=row.team_id,
            overall_pick=row.overall_pick,
            round_number=row.round_number,
            board_scarcity_score=float(row.board_scarcity_score or 0),
            best_available_player_score=float(row.best_available_player_score or 0),
            top_need_position=row.top_need_position,
        )
        for row in rows
    ]
