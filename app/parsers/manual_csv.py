import csv
from pathlib import Path

from app.schemas.parsed import ParsedMockDraft, ParsedPick


def parse_manual_csv(path: Path, source_slug: str, draft_year: int, title: str) -> ParsedMockDraft:
    picks: list[ParsedPick] = []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            picks.append(
                ParsedPick(
                    round_number=int(row["round_number"]),
                    overall_pick=int(row["overall_pick"]),
                    original_team=row.get("original_team") or None,
                    current_team=row.get("current_team") or None,
                    traded=(row.get("traded", "false").lower() == "true"),
                    player_name=row["player_name"],
                    position=row.get("position") or None,
                    school=row.get("school") or None,
                )
            )

    return ParsedMockDraft(
        source_slug=source_slug,
        article_url=f"manual://{path.name}",
        title=title,
        author_name=None,
        published_at=None,
        updated_at=None,
        draft_year=draft_year,
        picks=picks,
    )
