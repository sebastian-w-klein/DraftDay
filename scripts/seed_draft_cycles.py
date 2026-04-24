import argparse
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select

# Support running as `python scripts/seed_draft_cycles.py` in containers.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.entities import DraftCycle


def main() -> None:
    parser = argparse.ArgumentParser(description="Upsert DraftCycle rows by NFL draft calendar year.")
    parser.add_argument("--min-year", type=int, default=1980, help="First draft class year (inclusive).")
    parser.add_argument("--max-year", type=int, default=2030, help="Last draft class year (inclusive).")
    args = parser.parse_args()

    created = 0
    with SessionLocal() as db:
        for year in range(args.min_year, args.max_year + 1):
            row = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
            if row is None:
                db.add(
                    DraftCycle(
                        year=year,
                        start_date=date(year - 1, 8, 1),
                        draft_date=date(year, 4, 25),
                    )
                )
                created += 1
        db.commit()
    print(f"Seeded draft cycles (range {args.min_year}-{args.max_year}); new rows={created}.")


if __name__ == "__main__":
    main()
