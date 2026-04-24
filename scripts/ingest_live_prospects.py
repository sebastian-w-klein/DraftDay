import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.ingestion.prospects_live import ingest_live_tankathon_prospects  # noqa: E402


def main() -> None:
    draft_year = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 128
    with SessionLocal() as db:
        count = ingest_live_tankathon_prospects(db, draft_year=draft_year, limit=limit)
    print(f"Ingested {count} live prospects for {draft_year}.")


if __name__ == "__main__":
    main()
