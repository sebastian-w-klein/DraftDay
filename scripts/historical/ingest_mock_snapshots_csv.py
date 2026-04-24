"""
Scaffold: import archived mock drafts from CSV into the normal `mock_articles` / `mock_picks` path.

Expected columns:
  source_slug, article_url, title, draft_year, published_at_iso,
  overall_pick, round_number, team_abbrev, player_name, position, school

Each unique (source_slug, article_url, content_hash) becomes one article; rows with same article_url
group into one ParsedMockDraft-style ingest (batched in memory then upsert_mock_draft per article).

For large files, prefer splitting by article_url or extend this script to stream by article.

Usage:
  python scripts/historical/ingest_mock_snapshots_csv.py path/to/mocks.csv --source-key nflmdb-archive
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.ingestion.service import upsert_mock_draft  # noqa: E402
from app.models.entities import HistoricalIngestBatch, Source  # noqa: E402
from app.schemas.parsed import ParsedMockDraft, ParsedPick  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--source-key", default="csv-import")
    parser.add_argument("--dry-run", action="store_true", help="Validate rows and sources only.")
    args = parser.parse_args()

    if not args.csv_path.is_file():
        print(f"File not found: {args.csv_path}")
        sys.exit(1)

    articles: dict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    failed = 0
    inserted_articles = 0
    with args.csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                key = (
                    row["source_slug"].strip(),
                    row["article_url"].strip(),
                    int(row["draft_year"].strip()),
                )
                articles[key].append(row)
            except (KeyError, ValueError, AttributeError):
                failed += 1

    with SessionLocal() as db:
        batch = HistoricalIngestBatch(
            data_family="mock_snapshots",
            source_key=args.source_key,
            status="running",
            started_at=datetime.utcnow(),
            artifact_path=str(args.csv_path.resolve()),
        )
        db.add(batch)
        db.flush()

        for (slug, url, year), picks in articles.items():
            if db.scalar(select(Source).where(Source.slug == slug)) is None:
                print(f"Unknown source_slug '{slug}' — register in sources first. Skipping article {url}.")
                failed += len(picks)
                continue
            parsed_picks: list[ParsedPick] = []
            title = picks[0].get("title", "").strip() or f"Historical mock {year}"
            published_raw = picks[0].get("published_at_iso", "").strip()
            published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00")) if published_raw else None
            for row in picks:
                try:
                    parsed_picks.append(
                        ParsedPick(
                            round_number=int(row["round_number"].strip()),
                            overall_pick=int(row["overall_pick"].strip()),
                            original_team=row.get("team_abbrev", "").strip() or None,
                            current_team=row.get("team_abbrev", "").strip() or None,
                            traded=False,
                            player_name=row["player_name"].strip(),
                            position=row.get("position", "").strip() or None,
                            school=row.get("school", "").strip() or None,
                        )
                    )
                except (KeyError, ValueError, AttributeError):
                    failed += 1
            if not parsed_picks:
                continue
            if args.dry_run:
                inserted_articles += 1
                continue
            upsert_mock_draft(
                db,
                ParsedMockDraft(
                    source_slug=slug,
                    article_url=url,
                    title=title,
                    author_name=None,
                    published_at=published_at,
                    updated_at=published_at,
                    draft_year=year,
                    picks=sorted(parsed_picks, key=lambda p: p.overall_pick),
                ),
            )
            inserted_articles += 1

        batch.rows_inserted = inserted_articles
        batch.rows_failed = failed
        batch.status = "completed" if not args.dry_run else "dry_run"
        batch.completed_at = datetime.utcnow()
        if articles:
            ys = [y for _, _, y in articles]
            batch.year_start = min(ys)
            batch.year_end = max(ys)
        db.commit()

    mode = "dry-run" if args.dry_run else "ingest"
    print(f"Mock snapshots ({mode}): articles={inserted_articles} failed_rows={failed}")


if __name__ == "__main__":
    main()
