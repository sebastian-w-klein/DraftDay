import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.entities import DraftCycle, Team


def _upsert_team(db, abbr: str, full_name: str, city: str) -> Team:
    row = db.scalar(select(Team).where(Team.abbreviation == abbr))
    if row is None:
        row = Team(abbreviation=abbr, full_name=full_name, city=city, conference=None, division=None, active=True)
        db.add(row)
        db.flush()
    return row


def _upsert_cycle(db, year: int) -> DraftCycle:
    row = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if row is None:
        row = DraftCycle(year=year, start_date=date(year - 1, 8, 1), draft_date=date(year, 4, 25))
        db.add(row)
        db.flush()
    return row


def main() -> None:
    """Minimal environment bootstrap only (no fabricated mocks or prospect rows).

    Populate mocks, prospects, rosters, and needs from ingestion scripts and
    historical CSV pipelines — not from this file.
    """
    with SessionLocal() as db:
        target_year = datetime.utcnow().year
        _upsert_cycle(db, target_year)
        _upsert_team(db, "TEN", "Tennessee Titans", "Tennessee")
        _upsert_team(db, "CLE", "Cleveland Browns", "Cleveland")
        _upsert_team(db, "NYG", "New York Giants", "New York")
        db.commit()
    print(f"Bootstrap: ensured draft cycle {target_year} and core teams only (no demo mocks).")


if __name__ == "__main__":
    main()
