from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.board_state import taken_normalized_names
from app.db.session import get_db
from app.schemas.intelligence import (
    ConsensusVsMlResponse,
    IntelligenceModelMetadataResponse,
    ModelMetadataResponse,
    PickPlayerProbsRequest,
    PickPlayerProbsResponse,
    PositionProbabilityResponse,
    RankedPlayerProbability,
    TeamNeedsResponse,
)
from backend.app.ml.inference.predictor import (
    compare_with_consensus,
    get_model_metadata,
    get_team_need_profile,
    predict_pick_players,
    predict_pick_position,
)

router = APIRouter(prefix="/api/v1/intelligence", tags=["draft-intelligence"])


@router.get("/team-needs", response_model=TeamNeedsResponse)
def team_needs(
    team: str = Query(..., min_length=2, max_length=8),
    year: int = Query(..., ge=2010, le=2100),
    db: Session = Depends(get_db),
) -> TeamNeedsResponse:
    payload = get_team_need_profile(db, team_abbr=team, year=year)
    return TeamNeedsResponse(**payload)


@router.get("/pick-position-probs", response_model=PositionProbabilityResponse)
def pick_position_probs(
    team: str = Query(..., min_length=2, max_length=8),
    pick: int = Query(..., ge=1, le=300),
    year: int = Query(..., ge=2010, le=2100),
    db: Session = Depends(get_db),
) -> PositionProbabilityResponse:
    try:
        result = predict_pick_position(db, team_abbr=team, pick=pick, year=year)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PositionProbabilityResponse(
        team=result.team,
        year=result.year,
        overall_pick=result.overall_pick,
        model_version=result.model_version,
        position_probabilities=result.position_probabilities,
        need_profile=result.need_profile,
        explanation_summary=result.explanation_summary,
    )


@router.post("/pick-player-probs", response_model=PickPlayerProbsResponse)
def pick_player_probs(payload: PickPlayerProbsRequest, db: Session = Depends(get_db)) -> PickPlayerProbsResponse:
    try:
        taken = (
            taken_normalized_names(db, payload.year, before_overall=payload.pick)
            if payload.board_aware
            else None
        )
        result = predict_pick_players(
            db,
            team_abbr=payload.team,
            pick=payload.pick,
            year=payload.year,
            candidate_payload=[item.model_dump() for item in payload.candidate_players] if payload.candidate_players else [],
            exclude_taken_normalized=taken,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PickPlayerProbsResponse(
        team=result.team,
        pick=result.overall_pick,
        year=result.year,
        model_version=result.model_version,
        ranked_players=[
            RankedPlayerProbability(
                player_name=item.player_name,
                position=item.position,
                probability=item.probability,
                need_component=item.need_component,
                talent_component=item.talent_component,
                context_component=item.context_component,
                superstar_override_score=item.superstar_override_score,
            )
            for item in result.ranked_players
        ],
        explanation_summary=result.explanation_summary,
    )


@router.get("/compare-with-consensus", response_model=ConsensusVsMlResponse)
def compare_consensus_vs_ml(
    team: str = Query(..., min_length=2, max_length=8),
    pick: int = Query(..., ge=1, le=300),
    year: int = Query(..., ge=2010, le=2100),
    board_aware: bool = Query(
        default=False,
        description="Exclude players already drafted before this pick (actual_draft_picks).",
    ),
    db: Session = Depends(get_db),
) -> ConsensusVsMlResponse:
    try:
        taken = taken_normalized_names(db, year, before_overall=pick) if board_aware else None
        result = compare_with_consensus(db, team_abbr=team, pick=pick, year=year, exclude_taken_normalized=taken)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ConsensusVsMlResponse(
        team=result.team,
        pick=result.overall_pick,
        year=result.year,
        consensus_top_players=result.consensus_top_players,
        ml_top_players=result.ml_top_players,
        overlap=result.overlap,
        disagreement_score=result.disagreement_score,
        divergence_explanation=result.divergence_explanation,
    )


@router.get("/model-metadata", response_model=IntelligenceModelMetadataResponse)
def model_metadata(db: Session = Depends(get_db)) -> IntelligenceModelMetadataResponse:
    models = get_model_metadata(db)
    return IntelligenceModelMetadataResponse(
        models=[
            ModelMetadataResponse(
                model_family=str(item["model_family"]),
                model_version=str(item["model_version"]),
                train_window=[int(item["train_window"][0]), int(item["train_window"][1])],
                validation_window=[item["validation_window"][0], item["validation_window"][1]],
                test_window=[item["test_window"][0], item["test_window"][1]],
                metrics=item["metrics"],
                feature_groups=[str(v) for v in item["feature_groups"]],
                training_timestamp=str(item["training_timestamp"]),
            )
            for item in models
        ]
    )
