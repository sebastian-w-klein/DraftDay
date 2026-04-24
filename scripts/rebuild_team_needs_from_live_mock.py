import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.models.entities import DraftCycle, MockPick, Source, Team, TeamPositionNeedFeature  # noqa: E402

SOURCE_SLUG = "tankathon-live-mock"
POSITIONS = ["QB", "OT", "EDGE", "CB", "WR", "DT", "IOL", "LB", "S", "RB", "TE"]


def main() -> None:
    year = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.utcnow().year
    with SessionLocal() as db:
        cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
        source = db.scalar(select(Source).where(Source.slug == SOURCE_SLUG))
        if cycle is None or source is None:
            print("Missing draft cycle or live mock source.")
            return
        teams = db.scalars(select(Team).where(Team.active == True)).all()  # noqa: E712

        picks = db.scalars(
            select(MockPick).where(
                MockPick.draft_cycle_id == cycle.id,
                MockPick.source_id == source.id,
                MockPick.round_number == 1,
                MockPick.current_team_id.is_not(None),
            )
        ).all()
        pick_pos_by_team = {int(p.current_team_id): (p.normalized_position or "UNK") for p in picks if p.current_team_id is not None}

        upserts = 0
        for team in teams:
            top_pos = pick_pos_by_team.get(team.id, "UNK")
            for idx, pos in enumerate(POSITIONS):
                base = 0.35 + ((idx % 5) * 0.07)
                if pos == top_pos:
                    base = 0.95
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
                            short_term_need_score=Decimal(str(round(base, 4))),
                            long_term_need_score=Decimal(str(round(max(0.2, base - 0.1), 4))),
                            overall_need_score=Decimal(str(round(base, 4))),
                        )
                    )
                else:
                    row.short_term_need_score = Decimal(str(round(base, 4)))
                    row.long_term_need_score = Decimal(str(round(max(0.2, base - 0.1), 4)))
                    row.overall_need_score = Decimal(str(round(base, 4)))
                upserts += 1
        db.commit()
    print(f"Rebuilt team needs from live mock for {year}: {upserts} rows.")


if __name__ == "__main__":
    main()
