from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import DraftCycle, ProspectFeature


@dataclass
class ProspectRow:
    player_id: int | None
    full_name: str
    position: str
    prospect_score: float
    superstar_potential_score: float
    consensus_rank: int | None


def load_prospect_rows(db: Session, year: int) -> list[ProspectRow]:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if cycle is None:
        return []
    rows = db.scalars(select(ProspectFeature).where(ProspectFeature.draft_cycle_id == cycle.id)).all()
    return [
        ProspectRow(
            player_id=row.player_id,
            full_name=row.full_name,
            position=row.position,
            prospect_score=float(row.production_score or 0),
            superstar_potential_score=float(row.superstar_potential_score or 0),
            consensus_rank=row.consensus_rank,
        )
        for row in rows
    ]
