import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.models.entities import DraftCycle, DraftOrderPick, Team, TeamPositionNeedFeature  # noqa: E402

POSITIONS = ["OT", "EDGE", "CB", "WR", "QB", "DT", "IOL", "LB", "S"]


def _score(seed: int, offset: int) -> float:
    return max(0.2, min(0.95, 0.2 + (((seed + offset) % 100) / 100.0) * 0.75))


def main() -> None:
    target_year = datetime.utcnow().year
    with SessionLocal() as db:
        cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == target_year))
        if cycle is None:
            print(f"Draft cycle {target_year} not found.")
            return
        teams = db.scalars(select(Team).where(Team.active == True)).all()  # noqa: E712
        upserts = 0
        for team in teams:
            pick_row = db.scalar(
                select(DraftOrderPick).where(
                    DraftOrderPick.draft_cycle_id == cycle.id,
                    DraftOrderPick.team_id == team.id,
                    DraftOrderPick.round_number == 1,
                )
            )
            pick_boost = 0 if pick_row is None else max(0, 16 - min(16, pick_row.overall_pick)) / 40.0
            seed = sum(ord(c) for c in team.abbreviation)
            for idx, pos in enumerate(POSITIONS):
                base = _score(seed, idx * 11) + pick_boost
                value = float(max(0.2, min(0.98, base)))
                row = db.scalar(
                    select(TeamPositionNeedFeature).where(
                        TeamPositionNeedFeature.draft_cycle_id == cycle.id,
                        TeamPositionNeedFeature.team_id == team.id,
                        TeamPositionNeedFeature.position == pos,
                    )
                )
                if row is None:
                    db.add(
                        TeamPositionNeedFeature(
                            draft_cycle_id=cycle.id,
                            team_id=team.id,
                            position=pos,
                            returning_snaps=Decimal("0.5"),
                            returning_starts=Decimal("0.5"),
                            avg_age=Decimal("0.5"),
                            avg_experience=Decimal("0.5"),
                            depth_count=3,
                            starter_continuity=Decimal("0.5"),
                            recent_draft_investment=Decimal("0.3"),
                            recent_free_agent_investment=Decimal("0.2"),
                            short_term_need_score=Decimal(str(round(value, 4))),
                            long_term_need_score=Decimal(str(round(max(0.2, value - 0.08), 4))),
                            overall_need_score=Decimal(str(round(value, 4))),
                        )
                    )
                upserts += 1
        db.commit()
    print(f"Seeded baseline team needs rows: {upserts} for {target_year}.")


if __name__ == "__main__":
    main()
