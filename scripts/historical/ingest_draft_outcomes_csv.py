"""
Load historical NFL draft outcomes from a CSV into `actual_draft_picks`.

Expected columns (header row required):
  draft_year, round_number, overall_pick, team_abbrev, player_name

Registers a row in `historical_ingest_batches` for traceability.

Usage:
  python scripts/historical/ingest_draft_outcomes_csv.py path/to/outcomes.csv \\
      --source-key pfr-export --notes "optional note"
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.ingestion.nflverse_team_aliases import nflverse_team_to_current  # noqa: E402
from app.models.entities import ActualDraftPick, DraftCycle, HistoricalIngestBatch, Team  # noqa: E402
from app.normalization.normalizers import normalize_player_name  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--source-key", default="csv-import", help="Logical name for this file / provider.")
    parser.add_argument("--notes", default=None)
    args = parser.parse_args()

    if not args.csv_path.is_file():
        print(f"File not found: {args.csv_path}")
        sys.exit(1)

    inserted = 0
    failed = 0
    with SessionLocal() as db:
        batch = HistoricalIngestBatch(
            data_family="draft_outcomes",
            source_key=args.source_key,
            year_start=None,
            year_end=None,
            status="running",
            started_at=datetime.utcnow(),
            artifact_path=str(args.csv_path.resolve()),
            notes=args.notes,
        )
        db.add(batch)
        db.flush()

        years: set[int] = set()
        with args.csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                try:
                    year = int(row["draft_year"].strip())
                    rnd = int(row["round_number"].strip())
                    overall = int(row["overall_pick"].strip())
                    abbrev = row["team_abbrev"].strip().upper()
                    raw_name = row["player_name"].strip()
                except (KeyError, ValueError, AttributeError):
                    failed += 1
                    continue

                years.add(year)
                cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
                team = db.scalar(select(Team).where(Team.abbreviation == abbrev))
                if team is None:
                    mapped = nflverse_team_to_current(abbrev, year)
                    if mapped != abbrev:
                        team = db.scalar(select(Team).where(Team.abbreviation == mapped))
                if cycle is None or team is None:
                    failed += 1
                    continue

                existing = db.scalar(
                    select(ActualDraftPick).where(
                        ActualDraftPick.draft_cycle_id == cycle.id,
                        ActualDraftPick.overall_pick == overall,
                    )
                )
                if existing is not None:
                    db.delete(existing)
                    db.flush()

                db.add(
                    ActualDraftPick(
                        draft_cycle_id=cycle.id,
                        round_number=rnd,
                        overall_pick=overall,
                        team_id=team.id,
                        player_id=None,
                        normalized_player_name=normalize_player_name(raw_name),
                    )
                )
                inserted += 1

        batch.year_start = min(years) if years else None
        batch.year_end = max(years) if years else None
        batch.rows_inserted = inserted
        batch.rows_failed = failed
        batch.status = "completed"
        batch.completed_at = datetime.utcnow()
        db.commit()

    print(f"Historical draft outcomes: inserted={inserted} failed={failed}")


if __name__ == "__main__":
    main()
