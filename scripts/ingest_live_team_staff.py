import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.ingestion.team_staff_live import ingest_live_team_staff  # noqa: E402


def main() -> None:
    draft_year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    with SessionLocal() as db:
        count = ingest_live_team_staff(db, draft_year=draft_year)
    print(f"Ingested live staff rows for {count} teams in {draft_year}.")


if __name__ == "__main__":
    main()
