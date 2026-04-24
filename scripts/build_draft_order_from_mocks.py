import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.models.entities import DraftCycle, DraftOrderPick, MockPick, Team  # noqa: E402


def main() -> None:
    target_year = datetime.utcnow().year
    with SessionLocal() as db:
        cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == target_year))
        if cycle is None:
            print(f"Draft cycle {target_year} not found.")
            return

        picks = db.scalars(
            select(MockPick).where(
                MockPick.draft_cycle_id == cycle.id,
                MockPick.current_team_id.is_not(None),
            )
        ).all()
        by_pick: dict[int, Counter[int]] = defaultdict(Counter)
        by_round: dict[int, int] = {}
        for row in picks:
            by_pick[row.overall_pick][int(row.current_team_id)] += 1
            by_round[row.overall_pick] = row.round_number

        upserts = 0
        for overall_pick, counter in sorted(by_pick.items()):
            team_id, _ = counter.most_common(1)[0]
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
                        round_number=int(by_round.get(overall_pick, 1)),
                        overall_pick=overall_pick,
                        team_id=team_id,
                        source_name="mock-consensus-draft-order",
                    )
                )
            else:
                existing.team_id = team_id
                existing.round_number = int(by_round.get(overall_pick, existing.round_number))
                existing.source_name = "mock-consensus-draft-order"
            upserts += 1

        db.commit()
        teams = db.scalars(select(Team)).all()
        print(f"Built {upserts} draft-order slots from mocks for {target_year}. Teams in DB: {len(teams)}")


if __name__ == "__main__":
    main()
