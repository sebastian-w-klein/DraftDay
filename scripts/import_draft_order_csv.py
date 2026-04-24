import csv
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.models.entities import DraftCycle, DraftOrderPick, Team  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_draft_order_csv.py <csv_path> [draft_year]")
        return
    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return
    draft_year = int(sys.argv[2]) if len(sys.argv) > 2 else 2026

    with SessionLocal() as db:
        cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == draft_year))
        if cycle is None:
            print(f"Draft cycle not found: {draft_year}")
            return

        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        upserts = 0
        for row in rows:
            overall_pick = int(row["overall_pick"])
            round_number = int(row.get("round_number") or 1)
            team_abbr = str(row["team_abbreviation"]).upper()
            team = db.scalar(select(Team).where(Team.abbreviation == team_abbr))
            if team is None:
                continue
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
                        round_number=round_number,
                        overall_pick=overall_pick,
                        team_id=team.id,
                        source_name="csv-draft-order",
                    )
                )
            else:
                existing.round_number = round_number
                existing.team_id = team.id
                existing.source_name = "csv-draft-order"
            upserts += 1
        db.commit()
    print(f"Imported {upserts} draft-order rows for {draft_year}.")


if __name__ == "__main__":
    main()
