"""
Scaffold: load prior-season roster snapshots for need-model features.

Expected columns:
  draft_year, team_abbrev, player_name, position,
  age, experience_years, games_played, games_started, snaps,
  under_contract, starter_flag, injury_flag

Rows map to `team_roster_snapshots` for the given draft_year cycle.

Usage:
  python scripts/historical/ingest_roster_snapshots_csv.py path/to/rosters.csv --source-key nflverse-rosters
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.entities import DraftCycle, HistoricalIngestBatch, Team, TeamRosterSnapshot  # noqa: E402
from app.normalization.normalizers import normalize_player_name, normalize_position  # noqa: E402


def _bool_cell(val: str | None) -> bool | None:
    if val is None or val.strip() == "":
        return None
    return val.strip().lower() in {"1", "true", "t", "yes", "y"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--source-key", default="csv-import")
    args = parser.parse_args()

    if not args.csv_path.is_file():
        print(f"File not found: {args.csv_path}")
        sys.exit(1)

    inserted = 0
    failed = 0
    years: set[int] = set()

    with SessionLocal() as db:
        batch = HistoricalIngestBatch(
            data_family="roster_snapshots",
            source_key=args.source_key,
            status="running",
            started_at=datetime.utcnow(),
            artifact_path=str(args.csv_path.resolve()),
        )
        db.add(batch)
        db.flush()

        with args.csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                try:
                    year = int(row["draft_year"].strip())
                    abbrev = row["team_abbrev"].strip().upper()
                    pname = row["player_name"].strip()
                    pos = row["position"].strip()
                except (KeyError, ValueError, AttributeError):
                    failed += 1
                    continue

                years.add(year)
                cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
                team = db.scalar(select(Team).where(Team.abbreviation == abbrev))
                if cycle is None or team is None:
                    failed += 1
                    continue

                db.add(
                    TeamRosterSnapshot(
                        draft_cycle_id=cycle.id,
                        team_id=team.id,
                        player_name=pname,
                        normalized_player_name=normalize_player_name(pname),
                        position=normalize_position(pos) or pos,
                        age=Decimal(row["age"]) if row.get("age", "").strip() else None,
                        experience_years=Decimal(row["experience_years"]) if row.get("experience_years", "").strip() else None,
                        games_played=int(row["games_played"]) if row.get("games_played", "").strip() else None,
                        games_started=int(row["games_started"]) if row.get("games_started", "").strip() else None,
                        snaps=int(row["snaps"]) if row.get("snaps", "").strip() else None,
                        under_contract=_bool_cell(row.get("under_contract")),
                        starter_flag=_bool_cell(row.get("starter_flag")),
                        injury_flag=_bool_cell(row.get("injury_flag")),
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

    print(f"Roster snapshots: inserted={inserted} failed={failed}")


if __name__ == "__main__":
    main()
