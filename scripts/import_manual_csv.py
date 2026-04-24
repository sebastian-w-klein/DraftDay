import sys
from pathlib import Path

# Support running as `python scripts/import_manual_csv.py` in containers.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.ingestion.service import upsert_mock_draft
from app.parsers.manual_csv import parse_manual_csv


def main() -> None:
    path = Path("data/manual_mock.csv")
    parsed = parse_manual_csv(
        path=path,
        source_slug="manual",
        draft_year=2026,
        title="Manual Import",
    )
    with SessionLocal() as db:
        article = upsert_mock_draft(db, parsed)
        print(f"Imported article id={article.id}")


if __name__ == "__main__":
    main()
