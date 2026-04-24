import json
import pickle
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.analytics.consensus import pick_consensus
from app.board_state import board_cache_suffix
from app.models.entities import (
    CandidatePlayerFeature,
    DraftCycle,
    MlModelRun,
    MlPrediction,
    MockPick,
    PickContextFeature,
    ProspectFeature,
    Team,
    TeamPositionNeedFeature,
)
from backend.app.ml.data.roster_loader import load_roster_rows
from backend.app.ml.explainability.grouped_explanations import grouped_feature_explanations
from backend.app.ml.features.candidate_features import CandidateInput, build_candidate_features
from backend.app.ml.features.roster_strength import (
    adjusted_need_map_for_team,
    roster_strength_proxy,
)
from app.normalization.normalizers import normalize_player_name
from backend.app.ml.models.player_model import PlayerModel, PlayerModelBundle
from backend.app.ml.models.position_model import PositionModelBundle


@dataclass
class PositionPredictionResult:
    team: str
    year: int
    overall_pick: int
    model_version: str
    position_probabilities: dict[str, float]
    need_profile: list[dict[str, float | str | int]]
    explanation_summary: dict[str, float | str | int]


@dataclass
class PlayerPredictionItem:
    player_name: str
    position: str
    probability: float
    need_component: float
    talent_component: float
    context_component: float
    superstar_override_score: float


@dataclass
class PlayerPredictionResult:
    team: str
    year: int
    overall_pick: int
    model_version: str
    ranked_players: list[PlayerPredictionItem]
    explanation_summary: dict[str, float | str | int]


@dataclass
class ComparisonResult:
    team: str
    year: int
    overall_pick: int
    consensus_top_players: list[dict[str, float | str]]
    ml_top_players: list[dict[str, float | str]]
    overlap: list[str]
    disagreement_score: float
    divergence_explanation: dict[str, float | str | int]


def get_team_need_profile(db: Session, team_abbr: str, year: int) -> dict[str, object]:
    team = db.scalar(select(Team).where(Team.abbreviation == team_abbr.upper()))
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if team is None or cycle is None:
        return {"team": team_abbr.upper(), "year": year, "needs": [], "top_need_positions": []}

    rows = db.scalars(
        select(TeamPositionNeedFeature).where(
            TeamPositionNeedFeature.team_id == team.id,
            TeamPositionNeedFeature.draft_cycle_id == cycle.id,
        )
    ).all()
    roster = load_roster_rows(db, year)
    adjusted = adjusted_need_map_for_team(db, team.id, year)
    ranked = sorted(
        rows,
        key=lambda row: float(adjusted.get(row.position, float(row.overall_need_score or 0))),
        reverse=True,
    )
    needs = [
        {
            "position": row.position,
            "short_term_need_score": float(row.short_term_need_score or 0),
            "long_term_need_score": float(row.long_term_need_score or 0),
            "overall_need_score": float(adjusted.get(row.position, float(row.overall_need_score or 0))),
            "feature_summary": {
                "returning_snaps": float(row.returning_snaps or 0),
                "returning_starts": float(row.returning_starts or 0),
                "avg_age": float(row.avg_age or 0),
                "avg_experience": float(row.avg_experience or 0),
                "depth_count": float(row.depth_count or 0),
                "starter_continuity": float(row.starter_continuity or 0),
                "roster_strength_proxy": roster_strength_proxy(team.id, row.position, roster),
                "overall_need_score_unadjusted": float(row.overall_need_score or 0),
            },
        }
        for row in ranked
    ]
    return {
        "team": team.abbreviation,
        "year": year,
        "needs": needs,
        "top_need_positions": [n["position"] for n in needs[:3]],
        "feature_summary": needs[:5],
    }


def predict_pick_position(db: Session, team_abbr: str, pick: int, year: int) -> PositionPredictionResult:
    team = db.scalar(select(Team).where(Team.abbreviation == team_abbr.upper()))
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if team is None or cycle is None:
        raise ValueError("Team or year not found")

    model_run = db.scalar(
        select(MlModelRun)
        .where(MlModelRun.model_family == "position_model")
        .order_by(desc(MlModelRun.created_at))
    )
    bundle: PositionModelBundle | None = None
    model_version = "position-heuristic-fallback-v1"
    if model_run is not None:
        artifact_path = Path(model_run.artifact_path)
        if artifact_path.exists():
            bundle = _load_bundle(artifact_path)
            model_version = model_run.model_version

    ctx = db.scalar(
        select(PickContextFeature).where(
            PickContextFeature.draft_cycle_id == cycle.id,
            PickContextFeature.team_id == team.id,
            PickContextFeature.overall_pick == pick,
        )
    )
    needs = db.scalars(
        select(TeamPositionNeedFeature).where(
            TeamPositionNeedFeature.draft_cycle_id == cycle.id,
            TeamPositionNeedFeature.team_id == team.id,
        )
    ).all()
    need_adjusted = adjusted_need_map_for_team(db, team.id, year)
    top_need = max(
        needs,
        key=lambda r: float(need_adjusted.get(r.position, float(r.overall_need_score or 0))),
        default=None,
    )
    if ctx and ctx.top_need_position:
        top_pos_pick = str(ctx.top_need_position)
    else:
        top_pos_pick = top_need.position if top_need else "UNK"
    row = {
        "need_score": float(need_adjusted.get(top_need.position, top_need.overall_need_score))
        if top_need is not None
        else 0.5,
        "board_scarcity_score": float(ctx.board_scarcity_score or 0) if ctx else 0.0,
        "best_available_player_score": float(ctx.best_available_player_score or 0) if ctx else 0.0,
        "overall_pick": pick,
        "round_number": int(ctx.round_number) if ctx else 1,
        "top_need_position": top_pos_pick,
    }
    serving_version = f"{model_version}-need-guard-v3-roster"
    cached = _read_prediction_cache(
        db,
        cycle_id=cycle.id,
        team_id=team.id,
        overall_pick=pick,
        prediction_type="position_probs",
        model_version=serving_version,
    )
    if cached is not None:
        sorted_probs = {str(k): float(v) for k, v in cached["position_probabilities"].items()}
    else:
        if bundle is not None:
            probs = bundle.pipeline.predict_proba([row])[0]
            prob_map = {label: float(prob) for label, prob in zip(bundle.class_labels, probs)}
            sorted_probs = dict(sorted(prob_map.items(), key=lambda item: item[1], reverse=True))
        else:
            # Heuristic fallback keeps API usable on fresh databases.
            top_position = str(row["top_need_position"] or "OT")
            sorted_probs = {
                top_position: 0.45,
                "OT": 0.2 if top_position != "OT" else 0.1,
                "EDGE": 0.2 if top_position != "EDGE" else 0.1,
                "CB": 0.15 if top_position != "CB" else 0.1,
                "WR": 0.1 if top_position != "WR" else 0.05,
            }
            total = sum(sorted_probs.values()) or 1.0
            sorted_probs = {
                k: v / total for k, v in dict(sorted(sorted_probs.items(), key=lambda item: item[1], reverse=True)).items()
            }
        top_need_position = str(row["top_need_position"] or "UNK")
        top_need_score = float(row["need_score"] or 0.0)
        # Guardrail: keep extreme model outputs from overpowering very strong need signals.
        if (
            top_need_position in sorted_probs
            and top_need_score >= 0.85
            and float(sorted_probs.get(top_need_position, 0.0)) < 0.25
        ):
            target = 0.55
            remaining = max(0.0, 1.0 - target)
            other_sum = sum(v for k, v in sorted_probs.items() if k != top_need_position) or 1.0
            adjusted: dict[str, float] = {top_need_position: target}
            for label, prob in sorted_probs.items():
                if label == top_need_position:
                    continue
                adjusted[label] = (float(prob) / other_sum) * remaining
            sorted_probs = dict(sorted(adjusted.items(), key=lambda item: item[1], reverse=True))
        _write_prediction_cache(
            db,
            cycle_id=cycle.id,
            team_id=team.id,
            overall_pick=pick,
            prediction_type="position_probs",
            model_version=serving_version,
            payload={"position_probabilities": sorted_probs},
        )
    need_profile = [
        {
            "position": n.position,
            "overall_need_score": float(need_adjusted.get(n.position, float(n.overall_need_score or 0))),
        }
        for n in sorted(
            needs,
            key=lambda x: float(need_adjusted.get(x.position, float(x.overall_need_score or 0))),
            reverse=True,
        )[:6]
    ]
    return PositionPredictionResult(
        team=team.abbreviation,
        year=year,
        overall_pick=pick,
        model_version=serving_version,
        position_probabilities=sorted_probs,
        need_profile=need_profile,
        explanation_summary={
            "top_need_position": row["top_need_position"],
            "board_scarcity_score": row["board_scarcity_score"],
            "best_available_player_score": row["best_available_player_score"],
            "need_score": row["need_score"],
        },
    )


def get_model_metadata(db: Session) -> list[dict[str, object]]:
    families = ["need_model", "position_model", "player_model"]
    output: list[dict[str, object]] = []
    for family in families:
        run = db.scalar(
            select(MlModelRun)
            .where(MlModelRun.model_family == family)
            .order_by(desc(MlModelRun.created_at))
        )
        if run is None:
            continue
        output.append(
            {
                "model_family": family,
                "model_version": run.model_version,
                "train_window": [run.train_year_start, run.train_year_end],
                "validation_window": [run.validation_year_start, run.validation_year_end],
                "test_window": [run.test_year_start, run.test_year_end],
                "metrics": json.loads(run.metrics_json),
                "feature_groups": _feature_groups_for_family(family),
                "training_timestamp": run.created_at.isoformat(),
            }
        )
    return output


def _load_bundle(path: Path) -> PositionModelBundle:
    with path.open("rb") as handle:
        return pickle.load(handle)


def _ml_cache_prediction_type(base: str, taken: frozenset[str] | None) -> str:
    if not taken:
        return base[:64]
    suffix = board_cache_suffix(taken)
    combined = f"{base}_{suffix}"
    return combined[:64]


def predict_pick_players(
    db: Session,
    team_abbr: str,
    pick: int,
    year: int,
    candidate_payload: list[dict[str, object]],
    *,
    exclude_taken_normalized: frozenset[str] | None = None,
) -> PlayerPredictionResult:
    team = db.scalar(select(Team).where(Team.abbreviation == team_abbr.upper()))
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if team is None or cycle is None:
        raise ValueError("Team or year not found")

    needs = db.scalars(
        select(TeamPositionNeedFeature).where(
            TeamPositionNeedFeature.draft_cycle_id == cycle.id,
            TeamPositionNeedFeature.team_id == team.id,
        )
    ).all()
    need_map = adjusted_need_map_for_team(db, team.id, year)
    if not need_map:
        need_map = {n.position: float(n.overall_need_score or 0) for n in needs}
    ctx = db.scalar(
        select(PickContextFeature).where(
            PickContextFeature.draft_cycle_id == cycle.id,
            PickContextFeature.team_id == team.id,
            PickContextFeature.overall_pick == pick,
        )
    )
    board_scarcity_score = float(ctx.board_scarcity_score or 0) if ctx else 0.0
    taken = exclude_taken_normalized or frozenset()
    pred_type = _ml_cache_prediction_type("player_probs", exclude_taken_normalized)

    raw_payload = list(candidate_payload) if candidate_payload else _default_candidate_payload(
        db, cycle.id, pick, limit=24, exclude_normalized=taken
    )
    resolved_payload = _filter_candidates_by_board(raw_payload, taken)
    if not resolved_payload:
        resolved_payload = _default_candidate_payload(
            db, cycle.id, pick, limit=24, exclude_normalized=frozenset()
        )
    _assign_best_available_ranks(resolved_payload)
    candidates = [
        CandidateInput(
            player_id=(int(c["player_id"]) if c.get("player_id") is not None else None),
            player_name=str(c["player_name"]),
            position=str(c["position"]),
            prospect_score=float(c["prospect_score"]),
            superstar_potential_score=float(c["superstar_potential_score"]),
            consensus_rank=(int(c["consensus_rank"]) if c.get("consensus_rank") is not None else None),
            best_available_rank=(
                int(c["best_available_rank"]) if c.get("best_available_rank") is not None else None
            ),
            best_rank_in_position=(
                int(c["best_rank_in_position"]) if c.get("best_rank_in_position") is not None else None
            ),
            selected_label=False,
        )
        for c in resolved_payload
    ]
    feature_rows = build_candidate_features(need_map, board_scarcity_score, candidates)
    _cache_candidate_features(db, cycle.id, team.id, pick, feature_rows)

    model_run = db.scalar(
        select(MlModelRun).where(MlModelRun.model_family == "player_model").order_by(desc(MlModelRun.created_at))
    )
    probs: list[float]
    model_version: str
    if model_run is not None and Path(model_run.artifact_path).exists():
        model_version = model_run.model_version
        cached = _read_prediction_cache(
            db,
            cycle_id=cycle.id,
            team_id=team.id,
            overall_pick=pick,
            prediction_type=pred_type,
            model_version=model_version,
        )
        if cached is not None:
            probs = [float(item["probability"]) for item in cached["ranked_players"]]
            cached_ranked = sorted(cached["ranked_players"], key=lambda x: x["probability"], reverse=True)
            return PlayerPredictionResult(
                team=team.abbreviation,
                year=year,
                overall_pick=pick,
                model_version=model_version,
                ranked_players=[
                    PlayerPredictionItem(
                        player_name=str(item["player_name"]),
                        position=str(item["position"]),
                        probability=float(item["probability"]),
                        need_component=float(item["need_component"]),
                        talent_component=float(item["talent_component"]),
                        context_component=float(item["context_component"]),
                        superstar_override_score=float(item["superstar_override_score"]),
                    )
                    for item in cached_ranked
                ],
                explanation_summary={
                    "candidate_count": len(cached_ranked),
                    "top_need_position": max(need_map.items(), key=lambda kv: kv[1])[0] if need_map else "UNK",
                    "board_scarcity_score": board_scarcity_score,
                },
            )
        bundle = _load_player_bundle(Path(model_run.artifact_path))
        model = PlayerModel()
        probs = model.predict_proba(bundle, feature_rows)
    else:
        probs = [_heuristic_player_prob(row) for row in feature_rows]
        model_version = "player-heuristic-fallback-v1"

    ranked_items: list[PlayerPredictionItem] = []
    for row, prob in sorted(zip(feature_rows, probs), key=lambda item: item[1], reverse=True):
        need_component = float(row["team_need_score"])
        talent_component = (float(row["prospect_score"]) + float(row["superstar_potential_score"])) / 2.0
        context_component = 1.0 - min(1.0, (float(row["rank_gap_from_best_available"]) / 32.0))
        superstar_override = compute_superstar_override_score(
            need_score=need_component,
            talent_score=talent_component,
            predicted_probability=prob,
        )
        ranked_items.append(
            PlayerPredictionItem(
                player_name=str(row["candidate_player_name"]),
                position=str(row["position"]),
                probability=float(prob),
                need_component=need_component,
                talent_component=talent_component,
                context_component=context_component,
                superstar_override_score=superstar_override,
            )
        )

    result = PlayerPredictionResult(
        team=team.abbreviation,
        year=year,
        overall_pick=pick,
        model_version=model_version,
        ranked_players=ranked_items,
        explanation_summary={
            "candidate_count": len(ranked_items),
            "top_need_position": max(need_map.items(), key=lambda kv: kv[1])[0] if need_map else "UNK",
            "board_scarcity_score": board_scarcity_score,
        },
    )
    _write_prediction_cache(
        db,
        cycle_id=cycle.id,
        team_id=team.id,
        overall_pick=pick,
        prediction_type=pred_type,
        model_version=model_version,
        payload={
            "ranked_players": [
                {
                    "player_name": item.player_name,
                    "position": item.position,
                    "probability": item.probability,
                    "need_component": item.need_component,
                    "talent_component": item.talent_component,
                    "context_component": item.context_component,
                    "superstar_override_score": item.superstar_override_score,
                }
                for item in result.ranked_players
            ]
        },
    )
    return result


def _load_player_bundle(path: Path) -> PlayerModelBundle:
    with path.open("rb") as handle:
        return pickle.load(handle)


def _heuristic_player_prob(row: dict[str, object]) -> float:
    need = float(row["team_need_score"])
    prospect = float(row["prospect_score"])
    star = float(row["superstar_potential_score"])
    consensus_rank = float(row.get("consensus_rank") or 300)
    consensus_signal = max(0.0, 1.0 - (consensus_rank / 300.0))
    scarcity = float(row.get("positional_scarcity_score") or 0)
    score = (
        (0.3 * need)
        + (0.3 * prospect)
        + (0.2 * star)
        + (0.15 * consensus_signal)
        + (0.05 * scarcity)
    )
    return max(0.0, min(1.0, score))


def compute_superstar_override_score(
    need_score: float, talent_score: float, predicted_probability: float
) -> float:
    # High override when need is weaker but talent and selection probability remain strong.
    weak_need_signal = max(0.0, 1.0 - min(1.0, need_score))
    elite_talent_signal = max(0.0, min(1.0, (talent_score - 0.65) / 0.35))
    model_confidence_signal = max(0.0, min(1.0, (predicted_probability - 0.2) / 0.8))
    return max(0.0, min(1.0, weak_need_signal * elite_talent_signal * model_confidence_signal * 2.2))


def compare_with_consensus(
    db: Session,
    team_abbr: str,
    pick: int,
    year: int,
    *,
    exclude_taken_normalized: frozenset[str] | None = None,
) -> ComparisonResult:
    team = db.scalar(select(Team).where(Team.abbreviation == team_abbr.upper()))
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if team is None or cycle is None:
        raise ValueError("Team or year not found")

    model_run = db.scalar(
        select(MlModelRun).where(MlModelRun.model_family == "player_model").order_by(desc(MlModelRun.created_at))
    )
    model_version = model_run.model_version if model_run is not None else "player-heuristic-fallback-v1"
    cmp_cache_type = _ml_cache_prediction_type("consensus_vs_ml", exclude_taken_normalized)
    cached = _read_prediction_cache(
        db,
        cycle_id=cycle.id,
        team_id=team.id,
        overall_pick=pick,
        prediction_type=cmp_cache_type,
        model_version=model_version,
    )
    if cached is not None:
        return ComparisonResult(
            team=team.abbreviation,
            year=year,
            overall_pick=pick,
            consensus_top_players=cached["consensus_top_players"],
            ml_top_players=cached["ml_top_players"],
            overlap=cached["overlap"],
            disagreement_score=float(cached["disagreement_score"]),
            divergence_explanation=cached["divergence_explanation"],
        )

    consensus = pick_consensus(
        db, draft_year=year, overall_pick=pick, top_n=5, exclude_taken_normalized=exclude_taken_normalized
    )
    consensus_top_players = [
        {
            "player_name": item.player_name,
            "probability": item.probability,
            "weighted_probability": item.weighted_probability,
        }
        for item in consensus.top_players
    ]

    ml_result = predict_pick_players(
        db,
        team_abbr=team.abbreviation,
        pick=pick,
        year=year,
        candidate_payload=[],
        exclude_taken_normalized=exclude_taken_normalized,
    )
    ml_top_players = [
        {
            "player_name": p.player_name,
            "position": p.position,
            "probability": p.probability,
            "need_component": p.need_component,
            "talent_component": p.talent_component,
            "context_component": p.context_component,
            "superstar_override_score": p.superstar_override_score,
        }
        for p in ml_result.ranked_players[:5]
    ]

    consensus_names = [str(item["player_name"]).lower() for item in consensus_top_players[:5]]
    ml_names = [str(item["player_name"]).lower() for item in ml_top_players[:5]]
    overlap = sorted(list(set(consensus_names).intersection(set(ml_names))))
    disagreement_score = compute_disagreement_score(consensus_names, ml_names)
    top_ml = ml_result.ranked_players[0] if ml_result.ranked_players else None
    grouped = grouped_feature_explanations(ml_result.explanation_summary)
    divergence_explanation = {
        "agreement_count": len(overlap),
        "consensus_only_count": len([n for n in consensus_names if n not in ml_names]),
        "ml_only_count": len([n for n in ml_names if n not in consensus_names]),
        "top_ml_player": top_ml.player_name if top_ml else "N/A",
        "top_ml_superstar_override_score": float(top_ml.superstar_override_score) if top_ml else 0.0,
        "need_component": grouped["need_component"],
        "talent_component": grouped["talent_component"],
        "context_component": grouped["context_component"],
    }

    result = ComparisonResult(
        team=team.abbreviation,
        year=year,
        overall_pick=pick,
        consensus_top_players=consensus_top_players,
        ml_top_players=ml_top_players,
        overlap=overlap,
        disagreement_score=disagreement_score,
        divergence_explanation=divergence_explanation,
    )
    _write_prediction_cache(
        db,
        cycle_id=cycle.id,
        team_id=team.id,
        overall_pick=pick,
        prediction_type=cmp_cache_type,
        model_version=model_version,
        payload={
            "consensus_top_players": result.consensus_top_players,
            "ml_top_players": result.ml_top_players,
            "overlap": result.overlap,
            "disagreement_score": result.disagreement_score,
            "divergence_explanation": result.divergence_explanation,
        },
    )
    return result


def compute_disagreement_score(consensus_names: list[str], ml_names: list[str]) -> float:
    if not consensus_names and not ml_names:
        return 0.0
    union = set(consensus_names).union(set(ml_names))
    inter = set(consensus_names).intersection(set(ml_names))
    if not union:
        return 0.0
    return max(0.0, min(1.0, 1.0 - (len(inter) / len(union))))


def _cache_candidate_features(
    db: Session,
    cycle_id: int,
    team_id: int,
    pick: int,
    rows: list[dict[str, object]],
) -> None:
    db.query(CandidatePlayerFeature).filter(
        CandidatePlayerFeature.draft_cycle_id == cycle_id,
        CandidatePlayerFeature.team_id == team_id,
        CandidatePlayerFeature.overall_pick == pick,
    ).delete()
    for row in rows:
        db.add(
            CandidatePlayerFeature(
                draft_cycle_id=cycle_id,
                team_id=team_id,
                overall_pick=pick,
                round_number=1,
                candidate_player_id=row["candidate_player_id"],
                candidate_player_name=str(row["candidate_player_name"]),
                position=str(row["position"]),
                available_at_pick=bool(row["available_at_pick"]),
                team_need_score=float(row["team_need_score"]),
                prospect_score=float(row["prospect_score"]),
                superstar_potential_score=float(row["superstar_potential_score"]),
                positional_scarcity_score=float(row["positional_scarcity_score"]),
                consensus_rank=(int(row["consensus_rank"]) if row["consensus_rank"] is not None else None),
                rank_gap_from_best_available=float(row["rank_gap_from_best_available"]),
                rank_gap_within_position=float(row["rank_gap_within_position"]),
                selected_label=bool(row["selected_label"]),
            )
        )
    db.commit()


def _read_prediction_cache(
    db: Session,
    cycle_id: int,
    team_id: int,
    overall_pick: int,
    prediction_type: str,
    model_version: str,
) -> dict[str, object] | None:
    row = db.scalar(
        select(MlPrediction).where(
            MlPrediction.draft_cycle_id == cycle_id,
            MlPrediction.team_id == team_id,
            MlPrediction.overall_pick == overall_pick,
            MlPrediction.prediction_type == prediction_type,
            MlPrediction.model_version == model_version,
        )
    )
    if row is None:
        return None
    return json.loads(row.payload_json)


def _write_prediction_cache(
    db: Session,
    cycle_id: int,
    team_id: int,
    overall_pick: int,
    prediction_type: str,
    model_version: str,
    payload: dict[str, object],
) -> None:
    existing = db.scalar(
        select(MlPrediction).where(
            MlPrediction.draft_cycle_id == cycle_id,
            MlPrediction.team_id == team_id,
            MlPrediction.overall_pick == overall_pick,
            MlPrediction.prediction_type == prediction_type,
            MlPrediction.model_version == model_version,
        )
    )
    if existing is None:
        db.add(
            MlPrediction(
                draft_cycle_id=cycle_id,
                team_id=team_id,
                overall_pick=overall_pick,
                model_version=model_version,
                prediction_type=prediction_type,
                payload_json=json.dumps(payload),
                generated_at=datetime.utcnow(),
            )
        )
    else:
        existing.payload_json = json.dumps(payload)
        existing.generated_at = datetime.utcnow()
    db.commit()


def _feature_groups_for_family(family: str) -> list[str]:
    mapping = {
        "need_model": ["team_need", "roster_continuity", "age_curve", "experience_curve"],
        "position_model": ["team_need", "pick_context", "board_context", "consensus_signals"],
        "player_model": [
            "team_need",
            "prospect_quality",
            "superstar_signal",
            "rank_gap",
            "board_scarcity",
        ],
    }
    return mapping.get(family, ["unknown"])


def _candidate_row_player_key(row: dict[str, object]) -> str:
    name = str(row.get("player_name") or "")
    return normalize_player_name(name) or name.lower().strip()


def _filter_candidates_by_board(payload: list[dict[str, object]], taken: frozenset[str]) -> list[dict[str, object]]:
    if not taken:
        return list(payload)
    return [row for row in payload if _candidate_row_player_key(row) not in taken]


def _assign_best_available_ranks(payload: list[dict[str, object]]) -> None:
    if not payload:
        return
    order = sorted(
        range(len(payload)),
        key=lambda i: (payload[i].get("consensus_rank") is None, int(payload[i].get("consensus_rank") or 9999)),
    )
    for rank_pos, idx in enumerate(order, start=1):
        payload[idx]["best_available_rank"] = rank_pos


def _default_candidate_payload(
    db: Session,
    cycle_id: int,
    pick: int,
    limit: int = 20,
    *,
    exclude_normalized: frozenset[str] | None = None,
    prospect_scan_limit: int = 200,
) -> list[dict[str, object]]:
    exclude = exclude_normalized or frozenset()
    rows = db.scalars(
        select(ProspectFeature)
        .where(ProspectFeature.draft_cycle_id == cycle_id)
        .order_by(ProspectFeature.consensus_rank.asc().nulls_last())
        .limit(prospect_scan_limit)
    ).all()
    payload: list[dict[str, object]] = []
    for idx, row in enumerate(rows, start=1):
        key = normalize_player_name(row.full_name) or (row.full_name or "").lower().strip()
        if key in exclude:
            continue
        consensus_rank = row.consensus_rank or (row.big_board_rank or (pick + idx))
        payload.append(
            {
                "player_id": row.player_id,
                "player_name": row.full_name,
                "position": row.position,
                "prospect_score": float(row.production_score or 0),
                "superstar_potential_score": float(row.superstar_potential_score or 0),
                "consensus_rank": consensus_rank,
                "best_available_rank": 1,
                "best_rank_in_position": row.positional_rank or 1,
            }
        )
        if len(payload) >= limit:
            break
    if payload:
        _assign_best_available_ranks(payload)
        return payload

    cycle = db.scalar(select(DraftCycle).where(DraftCycle.id == cycle_id))
    if cycle is None:
        return []
    consensus = pick_consensus(
        db, draft_year=cycle.year, overall_pick=pick, top_n=limit, exclude_taken_normalized=exclude
    )
    fallback: list[dict[str, object]] = []
    candidates_from_consensus = consensus.top_players
    if not candidates_from_consensus:
        candidates_from_consensus = [
            type("ConsensusLike", (), {"player_name": n, "weighted_probability": 0.5})()
            for n in db.scalars(
                select(MockPick.normalized_player_name)
                .where(MockPick.draft_cycle_id == cycle_id)
                .distinct()
                .limit(limit)
            ).all()
        ]
    idx_out = 0
    for player in candidates_from_consensus:
        pkey = normalize_player_name(player.player_name) or str(player.player_name).lower().strip()
        if pkey in exclude:
            continue
        idx_out += 1
        position = (
            db.scalar(
                select(MockPick.normalized_position)
                .where(
                    MockPick.draft_cycle_id == cycle_id,
                    MockPick.normalized_player_name == str(player.player_name).lower(),
                    MockPick.normalized_position.is_not(None),
                )
                .limit(1)
            )
            or "UNK"
        )
        fallback.append(
            {
                "player_id": None,
                "player_name": player.player_name,
                "position": str(position),
                "prospect_score": float(player.weighted_probability),
                "superstar_potential_score": float(player.weighted_probability),
                "consensus_rank": idx_out,
                "best_available_rank": 1,
                "best_rank_in_position": 1,
            }
        )
        if len(fallback) >= limit:
            break
    if fallback:
        _assign_best_available_ranks(fallback)
    return fallback
