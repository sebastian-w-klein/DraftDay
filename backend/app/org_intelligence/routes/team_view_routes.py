from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import ActualDraftPick, DraftCycle, DraftOrderPick, Team
from app.schemas.team_view import (
    TeamViewBacktestResponse,
    TeamViewHistoryResponse,
    TeamViewOrgProfileResponse,
    TeamViewPlayerProbsRequest,
    TeamViewPlayerProbsResponse,
    TeamViewPositionProbsResponse,
    TeamViewSummaryResponse,
)
from backend.app.org_intelligence.inference.org_predictor import (
    get_org_adjusted_position_probs,
    get_org_adjusted_player_probs,
    get_org_profile,
    get_team_history_payload,
    get_team_view_summary,
    run_org_backtest,
)

router = APIRouter(prefix="/api/v1/team-view", tags=["team-view"])


@router.get("/org-profile", response_model=TeamViewOrgProfileResponse)
def team_org_profile(
    team: str = Query(..., min_length=2, max_length=8),
    year: int = Query(..., ge=2010, le=2100),
    db: Session = Depends(get_db),
) -> TeamViewOrgProfileResponse:
    try:
        return TeamViewOrgProfileResponse(**get_org_profile(db, team_abbr=team, year=year))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/history", response_model=TeamViewHistoryResponse)
def team_history(
    team: str = Query(..., min_length=2, max_length=8),
    year: int = Query(..., ge=2010, le=2100),
    lookback_years: int = Query(default=5, ge=1, le=12),
    db: Session = Depends(get_db),
) -> TeamViewHistoryResponse:
    try:
        return TeamViewHistoryResponse(
            **get_team_history_payload(db, team_abbr=team, year=year, lookback_years=lookback_years)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/position-probs", response_model=TeamViewPositionProbsResponse)
def team_position_probs(
    team: str = Query(..., min_length=2, max_length=8),
    pick: int = Query(..., ge=1, le=300),
    year: int = Query(..., ge=2010, le=2100),
    db: Session = Depends(get_db),
) -> TeamViewPositionProbsResponse:
    try:
        return TeamViewPositionProbsResponse(**get_org_adjusted_position_probs(db, team_abbr=team, pick=pick, year=year))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/player-probs", response_model=TeamViewPlayerProbsResponse)
def team_player_probs(payload: TeamViewPlayerProbsRequest, db: Session = Depends(get_db)) -> TeamViewPlayerProbsResponse:
    try:
        result = get_org_adjusted_player_probs(
            db,
            team_abbr=payload.team,
            pick=payload.pick,
            year=payload.year,
            candidate_players=[item.model_dump() for item in payload.candidate_players] if payload.candidate_players else [],
            board_aware=payload.board_aware,
        )
        return TeamViewPlayerProbsResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/summary", response_model=TeamViewSummaryResponse)
def team_summary(
    team: str = Query(..., min_length=2, max_length=8),
    year: int = Query(..., ge=2010, le=2100),
    pick: int = Query(..., ge=1, le=300),
    board_aware: bool = Query(
        default=False,
        description="Exclude players already drafted before this pick when building consensus and player rankings.",
    ),
    db: Session = Depends(get_db),
) -> TeamViewSummaryResponse:
    try:
        result = get_team_view_summary(db, team_abbr=team, year=year, pick=pick, board_aware=board_aware)
        return TeamViewSummaryResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/backtest", response_model=TeamViewBacktestResponse)
def team_view_backtest() -> TeamViewBacktestResponse:
    truths = ["OT", "QB", "CB"]
    base_probs = [{"OT": 0.4, "QB": 0.3, "CB": 0.3}, {"QB": 0.5, "OT": 0.25, "CB": 0.25}, {"CB": 0.45, "OT": 0.3, "QB": 0.25}]
    org_probs = [{"OT": 0.5, "QB": 0.25, "CB": 0.25}, {"QB": 0.55, "OT": 0.2, "CB": 0.25}, {"CB": 0.5, "OT": 0.25, "QB": 0.25}]
    consensus_probs = [{"OT": 0.35, "QB": 0.35, "CB": 0.3}, {"QB": 0.52, "OT": 0.22, "CB": 0.26}, {"CB": 0.4, "OT": 0.35, "QB": 0.25}]
    return TeamViewBacktestResponse(
        **run_org_backtest(
            base_prob_vectors=base_probs,
            org_prob_vectors=org_probs,
            consensus_prob_vectors=consensus_probs,
            truths=truths,
        )
    )


@router.get("/draft-context")
def team_draft_context(
    team: str = Query(..., min_length=2, max_length=8),
    year: int = Query(..., ge=2010, le=2100),
    db: Session = Depends(get_db),
) -> dict[str, int | str | None]:
    resolved_team = team.strip().upper()
    team_row = db.scalar(select(Team).where(Team.abbreviation == resolved_team))
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if team_row is None or cycle is None:
        raise HTTPException(status_code=404, detail="Team or year not found")

    order_counts = {
        int(round_number): int(count)
        for round_number, count in db.execute(
            select(DraftOrderPick.round_number, func.count(DraftOrderPick.id))
            .where(DraftOrderPick.draft_cycle_id == cycle.id)
            .group_by(DraftOrderPick.round_number)
        ).all()
    }
    actual_counts = {
        int(round_number): int(count)
        for round_number, count in db.execute(
            select(ActualDraftPick.round_number, func.count(ActualDraftPick.id))
            .where(ActualDraftPick.draft_cycle_id == cycle.id)
            .group_by(ActualDraftPick.round_number)
        ).all()
    }
    completed_rounds = [
        round_number
        for round_number, total in order_counts.items()
        if total > 0 and actual_counts.get(round_number, 0) >= total
    ]
    latest_completed_round = max(completed_rounds) if completed_rounds else 1

    next_pick_row = db.execute(
        select(DraftOrderPick.overall_pick, DraftOrderPick.round_number)
        .join(Team, Team.id == DraftOrderPick.team_id)
        .outerjoin(
            ActualDraftPick,
            and_(
                ActualDraftPick.draft_cycle_id == DraftOrderPick.draft_cycle_id,
                ActualDraftPick.overall_pick == DraftOrderPick.overall_pick,
            ),
        )
        .where(
            DraftOrderPick.draft_cycle_id == cycle.id,
            Team.id == team_row.id,
            ActualDraftPick.id.is_(None),
        )
        .order_by(DraftOrderPick.overall_pick.asc())
    ).first()

    return {
        "team": resolved_team,
        "year": year,
        "latest_completed_round": latest_completed_round,
        "team_next_overall_pick": int(next_pick_row[0]) if next_pick_row is not None else None,
        "team_next_round": int(next_pick_row[1]) if next_pick_row is not None else None,
    }
