"""
Download nflverse / nfldata draft pick history and write CSV for `ingest_draft_outcomes_csv.py`.

Source (CC BY-SA 4.0 — same lineage as nflverse; attribute nflverse / PFR in public use):
  https://raw.githubusercontent.com/nflverse/nfldata/master/data/draft_picks.csv

Upstream columns: season, team, round, pick, pfr_name, ...
Output columns: draft_year, round_number, overall_pick, team_abbrev, player_name

Prerequisite: `draft_cycles` rows must exist for years you import (see scripts/seed_draft_cycles.py).

Usage:
  python scripts/historical/download_nflverse_draft_outcomes.py -o data/nflverse_draft_outcomes.csv
  python scripts/historical/ingest_draft_outcomes_csv.py data/nflverse_draft_outcomes.csv \\
      --source-key nflverse-nfldata --notes "nfldata draft_picks.csv"
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.ingestion.nflverse_team_aliases import nflverse_team_to_current  # noqa: E402

NFLDATA_DRAFT_PICKS_URL = (
    "https://raw.githubusercontent.com/nflverse/nfldata/master/data/draft_picks.csv"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("data/nflverse_draft_outcomes.csv"),
        help="Path for import-ready CSV.",
    )
    parser.add_argument(
        "--min-year",
        type=int,
        default=None,
        help="Optional: only include season >= this year.",
    )
    parser.add_argument(
        "--max-year",
        type=int,
        default=None,
        help="Optional: only include season <= this year.",
    )
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    with urlopen(NFLDATA_DRAFT_PICKS_URL, timeout=120) as resp:  # noqa: S310
        text = resp.read().decode("utf-8")

    import io

    reader = csv.DictReader(io.StringIO(text))
    required = {"season", "team", "round", "pick", "pfr_name"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        print("Unexpected CSV schema from nflverse; expected columns:", sorted(required))
        sys.exit(1)

    with args.output.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(
            out,
            fieldnames=["draft_year", "round_number", "overall_pick", "team_abbrev", "player_name"],
        )
        writer.writeheader()
        for row in reader:
            try:
                year = int(row["season"])
                if args.min_year is not None and year < args.min_year:
                    continue
                if args.max_year is not None and year > args.max_year:
                    continue
                team_raw = row["team"].strip().upper()
                team = nflverse_team_to_current(team_raw, year)
                writer.writerow(
                    {
                        "draft_year": year,
                        "round_number": int(row["round"]),
                        "overall_pick": int(row["pick"]),
                        "team_abbrev": team,
                        "player_name": row["pfr_name"].strip(),
                    }
                )
                written += 1
            except (KeyError, ValueError, AttributeError):
                continue

    print(f"Wrote {written} rows to {args.output.resolve()}")


if __name__ == "__main__":
    main()
