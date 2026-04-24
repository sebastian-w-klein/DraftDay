from datetime import datetime
from hashlib import sha256

from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import (
    DraftCycle,
    MockArticle,
    MockPick,
    ParseStatus,
    Source,
    Team,
)
from app.normalization.normalizers import (
    normalize_player_name,
    normalize_position,
    normalize_school,
    normalize_team,
    normalize_text,
)
from app.schemas.parsed import ParsedMockDraft, ParsedPick


def _apply_parsed_teams_to_rows(db: Session, article_id: int, parsed: ParsedMockDraft) -> None:
    """Re-resolve team FKs from a fresh parse (e.g. improved normalize_team / resolve_team_id)."""
    by_overall: dict[int, ParsedPick] = {}
    for p in parsed.picks:
        by_overall.setdefault(p.overall_pick, p)
    rows = db.scalars(select(MockPick).where(MockPick.mock_article_id == article_id)).all()
    for row in rows:
        pick = by_overall.get(row.overall_pick)
        if pick is None:
            continue
        row.current_team_id = resolve_team_id(db, pick.current_team)
        row.original_team_id = resolve_team_id(db, pick.original_team)


def upsert_mock_draft(db: Session, parsed: ParsedMockDraft) -> MockArticle:
    source = db.scalar(select(Source).where(Source.slug == parsed.source_slug))
    if source is None:
        raise ValueError(f"Unknown source slug: {parsed.source_slug}")

    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == parsed.draft_year))
    if cycle is None:
        raise ValueError(f"Unknown draft cycle year: {parsed.draft_year}")

    content_hash = sha256(
        f"{parsed.article_url}|{parsed.title}|{len(parsed.picks)}".encode("utf-8")
    ).hexdigest()
    existing = db.scalar(
        select(MockArticle).where(
            MockArticle.source_id == source.id,
            MockArticle.article_url == parsed.article_url,
            MockArticle.content_hash == content_hash,
        )
    )
    if existing is not None:
        _apply_parsed_teams_to_rows(db, existing.id, parsed)
        return existing

    article = MockArticle(
        source_id=source.id,
        author_id=None,
        draft_cycle_id=cycle.id,
        title=parsed.title,
        article_url=parsed.article_url,
        canonical_url=parsed.article_url,
        published_at=parsed.published_at,
        updated_at=parsed.updated_at,
        fetched_at=datetime.utcnow(),
        content_hash=content_hash,
        raw_html_path=None,
        raw_text="manual/imported",
        parser_version="1.0.0",
        parse_status=ParseStatus.success,
    )
    db.add(article)
    db.flush()

    for pick in parsed.picks:
        current_team_id = resolve_team_id(db, pick.current_team)
        original_team_id = resolve_team_id(db, pick.original_team)
        db.add(
            MockPick(
                mock_article_id=article.id,
                draft_cycle_id=cycle.id,
                source_id=source.id,
                author_id=None,
                round_number=pick.round_number,
                overall_pick=pick.overall_pick,
                original_team_id=original_team_id,
                current_team_id=current_team_id,
                traded=pick.traded,
                player_id=None,
                raw_player_name=pick.player_name,
                normalized_player_name=normalize_player_name(pick.player_name),
                raw_position=pick.position,
                normalized_position=normalize_position(pick.position),
                raw_school=pick.school,
                normalized_school=normalize_school(pick.school),
                confidence_extraction=None,
            )
        )

    db.commit()
    db.refresh(article)
    return article


def resolve_team_id(db: Session, raw_team: str | None) -> int | None:
    if raw_team is None:
        return None
    s = str(raw_team).strip()
    if not s:
        return None
    normalized = normalize_team(s)
    if normalized:
        team = db.scalar(select(Team).where(Team.abbreviation == normalized.upper()[:8]))
        if team is not None:
            return team.id
        slug = slugify(normalized).upper()
        if slug and slug != normalized.upper():
            team = db.scalar(select(Team).where(Team.abbreviation == slug[:8]))
            if team is not None:
                return team.id
    key = normalize_text(s)
    team = db.scalar(select(Team).where(func.lower(Team.full_name) == key))
    if team is not None:
        return team.id
    city_matches = list(db.scalars(select(Team).where(func.lower(Team.city) == key)).all())
    if len(city_matches) == 1:
        return city_matches[0].id
    return None
