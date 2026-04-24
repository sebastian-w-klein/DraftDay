"""Helpers for trade-aware round-1 slot state (actual picks vs. current order)."""

from __future__ import annotations


def next_unfilled_round1_overall_for_team(
    filled_overalls: set[int],
    draft_order_slots: list[tuple[int, str]],
    team_abbr: str,
    *,
    max_overall: int = 32,
) -> int | None:
    """
    First overall in ``[1, max_overall]`` that is not yet filled with an actual pick
    and whose current draft-order holder matches ``team_abbr`` (case-insensitive).
    """
    want = team_abbr.strip().upper()
    if not want:
        return None
    for overall, abbr in draft_order_slots:
        if overall > max_overall:
            continue
        if overall in filled_overalls:
            continue
        if str(abbr).upper() == want:
            return overall
    return None


def compute_next_round1_overall_for_team(
    db: object,
    *,
    draft_cycle_id: int,
    team_abbr: str,
    max_overall: int = 32,
) -> int | None:
    """DB-backed next pick for a team using ``actual_draft_picks`` + ``draft_order_picks``."""
    from sqlalchemy import select

    from app.models.entities import ActualDraftPick, DraftOrderPick, Team

    filled_rows = db.scalars(
        select(ActualDraftPick.overall_pick).where(
            ActualDraftPick.draft_cycle_id == draft_cycle_id,
            ActualDraftPick.overall_pick <= max_overall,
        )
    ).all()
    filled = {int(o) for o in filled_rows}

    rows = db.execute(
        select(DraftOrderPick.overall_pick, Team.abbreviation)
        .join(Team, Team.id == DraftOrderPick.team_id)
        .where(
            DraftOrderPick.draft_cycle_id == draft_cycle_id,
            DraftOrderPick.overall_pick <= max_overall,
        )
        .order_by(DraftOrderPick.overall_pick.asc())
    ).all()
    slots = [(int(o), str(a)) for o, a in rows]
    return next_unfilled_round1_overall_for_team(filled, slots, team_abbr, max_overall=max_overall)
