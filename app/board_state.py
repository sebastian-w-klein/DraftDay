"""Live draft board: players already selected (``actual_draft_picks``)."""

from __future__ import annotations

from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import ActualDraftPick, DraftCycle


def taken_normalized_names(
    db: Session,
    draft_year: int,
    *,
    before_overall: int | None = None,
) -> frozenset[str]:
    """
    Normalized player keys for official picks in ``draft_year``.

    When ``before_overall`` is set (e.g. current slot), only picks with
    ``overall_pick < before_overall`` count — the board state *before* that selection.
    When ``None``, every recorded actual pick is included.
    """
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == draft_year))
    if cycle is None:
        return frozenset()
    q = select(ActualDraftPick.normalized_player_name).where(ActualDraftPick.draft_cycle_id == cycle.id)
    if before_overall is not None:
        q = q.where(ActualDraftPick.overall_pick < before_overall)
    rows = db.scalars(q).all()
    return frozenset(str(n).strip() for n in rows if n and str(n).strip())


def board_cache_suffix(taken: frozenset[str]) -> str:
    """Short stable suffix for cache keys when the board is non-empty."""
    if not taken:
        return ""
    digest = sha256("|".join(sorted(taken)).encode()).hexdigest()[:10]
    return f"b{digest}"
