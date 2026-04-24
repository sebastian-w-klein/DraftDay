from collections import defaultdict
from datetime import UTC, datetime
from math import exp

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.entities import DraftCycle, MockArticle, MockPick, Source, Team
from app.normalization.normalizers import normalize_player_name
from app.schemas.api import (
    ConsensusConfidence,
    LandingConfidence,
    PickConsensusResponse,
    PickProbability,
    PlayerLandingSpot,
    PlayerLandingSpotsResponse,
)

# Symmetric Dirichlet prior per category; +1 implicit OTHER category spreads uncertainty.
DEFAULT_SMOOTHING_ALPHA = 0.5
LOW_CONFIDENCE_MAX_SOURCES = 2
LOW_CONFIDENCE_MAX_SAMPLES = 4


def _equivalent_candidate_pool_size(overall_pick: int) -> int:
    """Larger implicit pools later in round-1.

    This reduces mass on a lone leader and avoids repeated 0.75 rows.
    """
    return min(28, max(6, 3 + overall_pick // 2))


def _landing_equivalent_pool_k(
    num_distinct_teams: int,
    total_mock_rows: int,
    unique_sources: int,
    unique_articles: int,
    earliest_overall_pick: int,
) -> int:
    """Dirichlet pool over listed teams + OTHER.

    It varies with evidence and slot; never one-size 81:19.
    """
    m = num_distinct_teams
    k_floor = m + 1
    n = total_mock_rows
    src = unique_sources
    arts = unique_articles
    ep = max(1, min(256, earliest_overall_pick))

    if m >= 2:
        return max(k_floor, min(24, k_floor + max(0, 8 - n // 4)))

    # m == 1: all rows name the same team.
    if n <= LOW_CONFIDENCE_MAX_SAMPLES:
        return max(k_floor, min(32, 4 + (30 // (n + 2))))
    if 5 <= n <= 6:
        return max(k_floor, min(10, 3 + (20 // (n + 2))))

    # Richer evidence means a smaller implicit OTHER pool, even with one source
    # when there are enough snapshots.
    k = 2 + max(0, min(6, 28 // (n + 2)))
    if src <= 1:
        k = max(k_floor, k - 1)
    if arts >= 8:
        k = max(k_floor, k - 1)
    if (ep <= 6 and n >= 6) or (ep <= 12 and n >= 10):
        k = max(k_floor, k - 1)
    if src >= 3:
        k = k_floor
    elif src == 2 and n >= 10:
        k = max(k_floor, min(k, k_floor + 1))
    return min(32, max(k_floor, k))


def _dirichlet_smoothed(
    category_values: dict[str, float],
    *,
    alpha: float = DEFAULT_SMOOTHING_ALPHA,
    equivalent_pool_k: int | None = None,
) -> tuple[dict[str, float], float, int]:
    """Symmetric Dirichlet over K categories (observed names + pooled OTHER for remaining slots)."""
    if not category_values:
        return {}, 0.0, 0
    m = len(category_values)
    k_floor = m + 1
    k = max(k_floor, int(equivalent_pool_k)) if equivalent_pool_k is not None else k_floor
    total = sum(float(v) for v in category_values.values())
    denom = total + alpha * k
    smoothed = {key: (float(val) + alpha) / denom for key, val in category_values.items()}
    p_other = (alpha * max(0, k - m)) / denom
    return smoothed, p_other, k


def _base_pick_query(draft_year: int) -> Select[tuple[MockPick, MockArticle, Source]]:
    return (
        select(MockPick, MockArticle, Source)
        .join(MockArticle, MockPick.mock_article_id == MockArticle.id)
        .join(Source, MockPick.source_id == Source.id)
        .join(DraftCycle, MockPick.draft_cycle_id == DraftCycle.id)
        .where(DraftCycle.year == draft_year)
    )


def pick_consensus(
    db: Session,
    draft_year: int,
    overall_pick: int,
    top_n: int = 5,
    *,
    exclude_taken_normalized: frozenset[str] | None = None,
) -> PickConsensusResponse:
    rows = db.execute(
        _base_pick_query(draft_year).where(MockPick.overall_pick == overall_pick)
    ).all()
    now = datetime.now(UTC)
    if not rows:
        return PickConsensusResponse(
            draft_year=draft_year,
            overall_pick=overall_pick,
            top_players=[],
            updated_at=now,
            consensus_confidence=None,
            board_aware=bool(exclude_taken_normalized),
            mock_rows_excluded=None,
        )

    taken = exclude_taken_normalized or frozenset()
    board_aware = bool(taken)
    excluded = 0

    counts: dict[str, int] = defaultdict(int)
    weighted: dict[str, float] = defaultdict(float)
    source_ids: set[int] = set()
    article_ids: set[int] = set()

    for pick, article, source in rows:
        key = pick.normalized_player_name
        if taken and key in taken:
            excluded += 1
            continue
        counts[key] += 1
        source_ids.add(source.id)
        article_ids.add(article.id)

        published = article.published_at or article.fetched_at
        published_utc = published if published.tzinfo else published.replace(tzinfo=UTC)
        age_days = max(0, (now - published_utc).days)
        recency_weight = exp(-age_days / max(1, source.recency_half_life_days))
        weighted[key] += float(source.default_weight) * recency_weight

    total = sum(counts.values())
    if total == 0:
        return PickConsensusResponse(
            draft_year=draft_year,
            overall_pick=overall_pick,
            top_players=[],
            updated_at=now,
            consensus_confidence=None,
            board_aware=board_aware,
            mock_rows_excluded=excluded if board_aware else None,
        )

    pool_k = _equivalent_candidate_pool_size(overall_pick)
    count_floats = {k: float(v) for k, v in counts.items()}
    smooth_counts, p_other_count, k_count = _dirichlet_smoothed(
        count_floats, equivalent_pool_k=pool_k
    )
    smooth_weighted, _, _ = _dirichlet_smoothed(weighted, equivalent_pool_k=pool_k)

    top = sorted(
        smooth_weighted.keys(),
        key=lambda name: (smooth_weighted[name], smooth_counts.get(name, 0.0)),
        reverse=True,
    )[:top_n]
    total_weighted = sum(weighted.values()) or 1.0

    low_confidence = (
        len(source_ids) <= LOW_CONFIDENCE_MAX_SOURCES or total <= LOW_CONFIDENCE_MAX_SAMPLES
    )
    confidence = ConsensusConfidence(
        sample_size=total,
        unique_sources=len(source_ids),
        unique_articles=len(article_ids),
        smoothing_alpha=DEFAULT_SMOOTHING_ALPHA,
        category_count=k_count,
        other_bucket_probability=float(p_other_count),
        low_confidence=low_confidence,
    )

    return PickConsensusResponse(
        draft_year=draft_year,
        overall_pick=overall_pick,
        updated_at=now,
        consensus_confidence=confidence,
        board_aware=board_aware,
        mock_rows_excluded=excluded if board_aware else None,
        top_players=[
            PickProbability(
                player_name=name,
                probability=float(smooth_counts[name]),
                weighted_probability=float(smooth_weighted[name]),
                raw_probability=float(counts[name] / total),
                raw_weighted_probability=float(weighted[name] / total_weighted),
            )
            for name in top
        ],
    )


def player_landing_spots(
    db: Session,
    draft_year: int,
    player_name: str,
    top_n: int = 5,
    *,
    context_overall_pick: int | None = None,
) -> PlayerLandingSpotsResponse:
    # Must match ingestion (`normalize_player_name`); `.lower().strip()` alone
    # misses punctuation and suffix rules.
    normalized = normalize_player_name(player_name) or player_name.lower().strip()
    now = datetime.now(UTC)

    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == draft_year))
    cycle_total_rows: int | None = None
    cycle_article_count: int | None = None
    if cycle is not None:
        cycle_total_rows = int(
            db.scalar(
                select(func.count())
                .select_from(MockPick)
                .where(MockPick.draft_cycle_id == cycle.id)
            )
            or 0
        )
        cycle_article_count = int(
            db.scalar(
                select(func.count())
                .select_from(MockArticle)
                .where(MockArticle.draft_cycle_id == cycle.id)
            )
            or 0
        )

    slot_rows_at_ctx: int | None = None
    if context_overall_pick is not None:
        slot_rows_at_ctx = int(
            db.scalar(
                select(func.count())
                .select_from(MockPick)
                .join(DraftCycle, MockPick.draft_cycle_id == DraftCycle.id)
                .where(
                    DraftCycle.year == draft_year,
                    MockPick.overall_pick == context_overall_pick,
                )
            )
            or 0
        )

    base_query = _base_pick_query(draft_year).where(MockPick.normalized_player_name == normalized)
    if context_overall_pick is not None:
        context_rows = db.execute(
            base_query.where(MockPick.overall_pick == context_overall_pick)
        ).all()
        rows = context_rows if context_rows else db.execute(base_query).all()
    else:
        rows = db.execute(base_query).all()
    if not rows:
        return PlayerLandingSpotsResponse(
            draft_year=draft_year,
            player_name=player_name,
            top_landing_spots=[],
            updated_at=now,
            landing_confidence=None,
            resolved_lookup_name=normalized,
            context_overall_pick=context_overall_pick,
            mock_rows_at_context_pick=slot_rows_at_ctx,
            draft_cycle_total_pick_rows=cycle_total_rows,
            draft_cycle_mock_articles=cycle_article_count,
        )

    team_map = {team.id: team.abbreviation for team in db.scalars(select(Team)).all()}
    counts: dict[str, int] = defaultdict(int)
    source_ids: set[int] = set()
    article_ids: set[int] = set()
    earliest_pick = 256
    for pick, article, source in rows:
        team_id = pick.current_team_id or pick.original_team_id
        if team_id is None:
            # Preserve unknown team rows as unknown; do not force a draft-order team.
            # For sparse day-2 data this can create misleading "100% <team>" outputs.
            continue
        team = team_map.get(team_id, "UNK")
        if team == "UNK":
            continue
        counts[team] += 1
        source_ids.add(source.id)
        article_ids.add(article.id)
        earliest_pick = min(earliest_pick, int(pick.overall_pick))

    total = len(rows)
    known_total = sum(counts.values())
    if known_total == 0:
        return PlayerLandingSpotsResponse(
            draft_year=draft_year,
            player_name=player_name,
            top_landing_spots=[],
            updated_at=now,
            landing_confidence=LandingConfidence(
                sample_size=total,
                unique_teams=0,
                unique_sources=len(source_ids),
                unique_articles=len(article_ids),
                smoothing_alpha=DEFAULT_SMOOTHING_ALPHA,
                category_count=0,
                other_bucket_probability=1.0,
                low_confidence=True,
            ),
            resolved_lookup_name=normalized,
            context_overall_pick=context_overall_pick,
            mock_rows_at_context_pick=slot_rows_at_ctx,
            draft_cycle_total_pick_rows=cycle_total_rows,
            draft_cycle_mock_articles=cycle_article_count,
        )
    unique_sources = len(source_ids)
    unique_articles = len(article_ids)
    count_floats = {k: float(v) for k, v in counts.items()}
    pool_k = _landing_equivalent_pool_k(
        len(counts), total, unique_sources, unique_articles, earliest_pick
    )
    smooth_teams, p_other, k_teams = _dirichlet_smoothed(count_floats, equivalent_pool_k=pool_k)
    # Order teams by observed counts so the API list matches what users see in raw mock rows.
    ranked = sorted(
        smooth_teams.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:top_n]
    low_confidence = (
        len(counts) <= 1
        or total <= LOW_CONFIDENCE_MAX_SAMPLES
        or unique_sources <= LOW_CONFIDENCE_MAX_SOURCES
    )
    landing_confidence = LandingConfidence(
        sample_size=total,
        unique_teams=len(counts),
        unique_sources=unique_sources,
        unique_articles=unique_articles,
        smoothing_alpha=DEFAULT_SMOOTHING_ALPHA,
        category_count=k_teams,
        other_bucket_probability=float(p_other),
        low_confidence=low_confidence,
    )
    return PlayerLandingSpotsResponse(
        draft_year=draft_year,
        player_name=player_name,
        updated_at=now,
        landing_confidence=landing_confidence,
        resolved_lookup_name=normalized,
        context_overall_pick=context_overall_pick,
        mock_rows_at_context_pick=slot_rows_at_ctx,
        draft_cycle_total_pick_rows=cycle_total_rows,
        draft_cycle_mock_articles=cycle_article_count,
        top_landing_spots=[
            PlayerLandingSpot(
                team=team,
                probability=float(prob),
                raw_probability=float(counts[team] / known_total),
            )
            for team, prob in ranked
        ],
    )
