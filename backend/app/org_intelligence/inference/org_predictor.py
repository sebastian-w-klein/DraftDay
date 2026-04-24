import json
from hashlib import sha256
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.consensus import pick_consensus
from app.board_state import board_cache_suffix, taken_normalized_names
from app.models.entities import (
    DraftCycle,
    DraftOrderPick,
    MockPick,
    ProspectFeature,
    Team,
    TeamPositionNeedFeature,
    TeamViewPrediction,
)
from backend.app.ml.features.roster_strength import adjusted_need_map_for_team
from backend.app.ml.inference.predictor import (
    _default_candidate_payload,
    get_team_need_profile,
    predict_pick_players,
    predict_pick_position,
)
from backend.app.org_intelligence.evaluation.backtests import (
    blend_consensus_ml_org,
    org_backtest_summary,
    ranked_labels,
)
from backend.app.org_intelligence.data.coach_loader import load_coach_profile_for_team_year
from backend.app.org_intelligence.data.gm_loader import load_gm_profile_for_team_year
from backend.app.org_intelligence.data.team_history_loader import load_org_tendency_row, load_team_history
from backend.app.org_intelligence.features.team_view_features import assemble_team_view_features
from backend.app.org_intelligence.models.integrated_team_prediction_model import IntegratedTeamPredictionModel
from backend.app.org_intelligence.models.org_prior_model import OrganizationalPriorModel, OrganizationalPriors


def get_org_profile(db: Session, team_abbr: str, year: int) -> dict[str, object]:
    team = db.scalar(select(Team).where(Team.abbreviation == team_abbr.upper()))
    if team is None:
        raise ValueError("Team not found")
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if cycle is None:
        raise ValueError("Year not found")
    cached = _read_team_view_cache(db, cycle.id, team.id, None, "team-view-org-profile-v2")
    if cached is not None:
        return cached
    gm = load_gm_profile_for_team_year(db, team.id, year)
    coach = load_coach_profile_for_team_year(db, team.id, year)
    org_row = load_org_tendency_row(db, team.id, year)
    features = assemble_team_view_features(gm, coach, org_row)
    priors = OrganizationalPriorModel().infer_priors(features)
    payload = {
        "team": team.abbreviation,
        "year": year,
        "gm_profile": None
        if gm is None
        else {
            "name": gm.gm_name,
            "years_of_prior_draft_history": gm.years_of_prior_draft_history,
            "offense_share": gm.offense_share,
            "defense_share": gm.defense_share,
            "need_follow_rate": gm.need_follow_rate,
            "bpa_proxy_rate": gm.bpa_proxy_rate,
            "favored_positions_json": gm.favored_positions_json,
        },
        "hc_profile": None
        if coach is None
        else {
            "name": coach.coach_name,
            "years_of_prior_history": coach.years_of_prior_history,
            "offensive_background": coach.offensive_background,
            "defensive_background": coach.defensive_background,
            "scheme_bias_label": coach.scheme_bias_label,
            "favored_positions_json": coach.favored_positions_json,
        },
        "regime_stability_score": priors.regime_stability_adjustment,
        "historical_tendency_metrics": {
            "offense_prior": priors.offense_prior,
            "defense_prior": priors.defense_prior,
            "trenches_prior": priors.trenches_prior,
            "skill_prior": priors.skill_prior,
            "need_follow_prior": priors.need_follow_prior,
            "bpa_deviation_prior": priors.bpa_deviation_prior,
        },
        "favored_positions_groups": {
            "gm": [] if gm is None or gm.favored_positions_json is None else _safe_json_list(gm.favored_positions_json),
            "hc": [] if coach is None or coach.favored_positions_json is None else _safe_json_list(coach.favored_positions_json),
        },
    }
    _write_team_view_cache(db, cycle.id, team.id, None, "team-view-org-profile-v2", payload)
    return payload


def get_team_history_payload(db: Session, team_abbr: str, year: int, lookback_years: int) -> dict[str, object]:
    team = db.scalar(select(Team).where(Team.abbreviation == team_abbr.upper()))
    if team is None:
        raise ValueError("Team not found")
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if cycle is None:
        raise ValueError("Year not found")
    cache_key = f"team-view-history-v2-lb{lookback_years}"
    cached = _read_team_view_cache(db, cycle.id, team.id, None, cache_key)
    if cached is not None:
        return cached
    rows = load_team_history(db, team.id, year, lookback_years=lookback_years)
    early = [r for r in rows if r.round_number <= 2]
    distribution: dict[str, int] = {}
    for row in early:
        key = row.position or "UNK"
        distribution[key] = distribution.get(key, 0) + 1
    payload = {
        "team": team.abbreviation,
        "year": year,
        "lookback_years": lookback_years,
        "recent_draft_history": [
            {
                "year": row.year,
                "overall_pick": row.overall_pick,
                "round_number": row.round_number,
                "position": row.position,
            }
            for row in rows
        ],
        "early_round_picks": [
            {
                "year": row.year,
                "overall_pick": row.overall_pick,
                "position": row.position,
            }
            for row in early
        ],
        "position_distributions": distribution,
        "need_alignment_summary": {"aligned_proxy_rate": 0.5, "deviation_proxy_rate": 0.5},
    }
    _write_team_view_cache(db, cycle.id, team.id, None, cache_key, payload)
    return payload


def get_org_adjusted_position_probs(db: Session, team_abbr: str, pick: int, year: int) -> dict[str, object]:
    team = db.scalar(select(Team).where(Team.abbreviation == team_abbr.upper()))
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if team is None or cycle is None:
        raise ValueError("Team or year not found")

    cached = _read_team_view_cache(db, cycle.id, team.id, pick, "team-view-position-v3")
    if cached is not None:
        return cached

    try:
        base = predict_pick_position(db, team_abbr=team.abbreviation, pick=pick, year=year)
        base_probs = base.position_probabilities
    except ValueError:
        # Fallback keeps Team View usable when position model artifacts are unavailable.
        base_probs = _fallback_position_probs_from_needs(db, cycle.id, team.id)
    gm = load_gm_profile_for_team_year(db, team.id, year)
    coach = load_coach_profile_for_team_year(db, team.id, year)
    org_row = load_org_tendency_row(db, team.id, year)
    features = assemble_team_view_features(gm, coach, org_row)
    priors = OrganizationalPriorModel().infer_priors(features)
    adjusted = IntegratedTeamPredictionModel().adjust_position_probabilities(base_probs, priors)
    delta = {k: adjusted.get(k, 0) - base_probs.get(k, 0) for k in set(base_probs).union(adjusted)}

    needs_payload = get_team_need_profile(db, team.abbreviation, year)
    top_needs = [
        {"position": n["position"], "overall_need_score": float(n["overall_need_score"])}
        for n in (needs_payload.get("needs") or [])[:5]
    ]
    payload = {
        "team": team.abbreviation,
        "year": year,
        "pick": pick,
        "base_ml_position_probabilities": base_probs,
        "org_adjusted_position_probabilities": adjusted,
        "delta_by_position": delta,
        "team_snapshot": {
            "team_name": team.full_name,
            "top_needs": top_needs,
            "gm": gm.gm_name if gm else None,
            "head_coach": coach.coach_name if coach else None,
            "current_draft_picks": _team_current_pick_list(db, cycle.id, team.id),
        },
    }
    _write_team_view_cache(db, cycle.id, team.id, pick, "team-view-position-v3", payload)
    return payload


def get_org_adjusted_player_probs(
    db: Session,
    team_abbr: str,
    pick: int,
    year: int,
    candidate_players: list[dict[str, object]],
    *,
    board_aware: bool = False,
) -> dict[str, object]:
    team = db.scalar(select(Team).where(Team.abbreviation == team_abbr.upper()))
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if team is None or cycle is None:
        raise ValueError("Team or year not found")
    taken = taken_normalized_names(db, year, before_overall=pick) if board_aware else None
    if candidate_players:
        resolved_candidates = candidate_players
    elif board_aware:
        resolved_candidates = _default_candidate_payload(
            db, cycle.id, pick, limit=12, exclude_normalized=taken or frozenset()
        )
    else:
        resolved_candidates = _default_candidate_players(db, cycle.id, year, pick)
    candidate_signature = _candidate_signature(resolved_candidates)
    cache_model_version = (
        f"team-view-player-v3_{board_cache_suffix(taken)}"[:64]
        if board_aware and taken
        else "team-view-player-v3"
    )
    cached = _read_team_view_cache(db, cycle.id, team.id, pick, cache_model_version)
    if cached is not None and cached.get("candidate_signature") == candidate_signature:
        return cached

    try:
        base = predict_pick_players(
            db,
            team_abbr=team.abbreviation,
            pick=pick,
            year=year,
            candidate_payload=resolved_candidates,
            exclude_taken_normalized=taken,
        )
        ranked_base = base.ranked_players
    except ValueError:
        ranked_base = _fallback_ranked_players(resolved_candidates)
    gm = load_gm_profile_for_team_year(db, team.id, year)
    coach = load_coach_profile_for_team_year(db, team.id, year)
    org_row = load_org_tendency_row(db, team.id, year)
    features = assemble_team_view_features(gm, coach, org_row)
    priors = OrganizationalPriorModel().infer_priors(features)

    adjusted_rows: list[dict[str, object]] = []
    raw_adjusted: list[float] = []
    for item in ranked_base:
        org_component = _organizational_component_for_position(item.position, priors)
        adjusted_prob = max(0.0, item.probability * (1.0 + ((org_component - 0.5) * 0.7)))
        raw_adjusted.append(adjusted_prob)
        adjusted_rows.append(
            {
                "player_name": item.player_name,
                "position": item.position,
                "base_probability": item.probability,
                "org_adjusted_probability": adjusted_prob,
                "need_component": item.need_component,
                "talent_component": item.talent_component,
                "context_component": item.context_component,
                "organizational_component": org_component,
            }
        )

    total = sum(raw_adjusted) or 1.0
    for row in adjusted_rows:
        row["org_adjusted_probability"] = float(row["org_adjusted_probability"]) / total
    adjusted_rows = sorted(adjusted_rows, key=lambda x: float(x["org_adjusted_probability"]), reverse=True)
    explanation = _build_integrated_explanation(
        team_abbr=team.abbreviation,
        top_position=adjusted_rows[0]["position"] if adjusted_rows else "N/A",
        top_player=adjusted_rows[0]["player_name"] if adjusted_rows else "N/A",
        priors=priors,
        organizational_component=float(adjusted_rows[0]["organizational_component"]) if adjusted_rows else 0.5,
    )
    payload = {
        "team": team.abbreviation,
        "year": year,
        "pick": pick,
        "candidate_signature": candidate_signature,
        "ranked_players": adjusted_rows,
        "integrated_explanation": explanation,
    }
    _write_team_view_cache(db, cycle.id, team.id, pick, cache_model_version, payload)
    return payload


def get_team_view_summary(
    db: Session,
    team_abbr: str,
    year: int,
    pick: int,
    candidate_players: list[dict[str, object]] | None = None,
    *,
    board_aware: bool = False,
) -> dict[str, object]:
    team = db.scalar(select(Team).where(Team.abbreviation == team_abbr.upper()))
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if team is None or cycle is None:
        raise ValueError("Team or year not found")
    taken = taken_normalized_names(db, year, before_overall=pick) if board_aware else None
    summary_cache_key = (
        f"team-view-summary-v3_{board_cache_suffix(taken)}"[:64]
        if board_aware and taken
        else "team-view-summary-v3"
    )
    cached = _read_team_view_cache(db, cycle.id, team.id, pick, summary_cache_key)
    if cached is not None:
        return cached

    org_profile = get_org_profile(db, team_abbr=team.abbreviation, year=year)
    pos = get_org_adjusted_position_probs(db, team_abbr=team.abbreviation, pick=pick, year=year)
    if candidate_players is not None:
        resolved_candidates = candidate_players
    elif board_aware:
        resolved_candidates = _default_candidate_payload(
            db, cycle.id, pick, limit=12, exclude_normalized=taken or frozenset()
        )
    else:
        resolved_candidates = _default_candidate_players(db, cycle.id, year, pick)
    players = get_org_adjusted_player_probs(
        db,
        team_abbr=team.abbreviation,
        pick=pick,
        year=year,
        candidate_players=resolved_candidates,
        board_aware=board_aware,
    )
    consensus = pick_consensus(
        db, draft_year=year, overall_pick=pick, top_n=5, exclude_taken_normalized=taken if taken else None
    )
    try:
        ml_result = predict_pick_players(
            db,
            team_abbr=team.abbreviation,
            pick=pick,
            year=year,
            candidate_payload=resolved_candidates,
            exclude_taken_normalized=taken,
        )
        ml_top = [
            {"player_name": p.player_name, "position": p.position, "probability": p.probability}
            for p in ml_result.ranked_players[:5]
        ]
    except ValueError:
        fallback = _fallback_ranked_players(resolved_candidates)
        ml_top = [
            {"player_name": p.player_name, "position": p.position, "probability": p.probability}
            for p in fallback[:5]
        ]

    payload = {
        "team": team.abbreviation,
        "year": year,
        "pick": pick,
        "team_snapshot": pos["team_snapshot"],
        "org_summary": {
            "gm_bias_summary": org_profile["historical_tendency_metrics"],
            "hc_bias_summary": {
                "offensive_background": None if org_profile["hc_profile"] is None else org_profile["hc_profile"].get("offensive_background"),
                "defensive_background": None if org_profile["hc_profile"] is None else org_profile["hc_profile"].get("defensive_background"),
            },
            "regime_stability_score": org_profile["regime_stability_score"],
            "need_vs_bpa_tendency": {
                "need_follow_prior": org_profile["historical_tendency_metrics"]["need_follow_prior"],
                "bpa_deviation_prior": org_profile["historical_tendency_metrics"]["bpa_deviation_prior"],
            },
        },
        "consensus_top_players": [
            {"player_name": p.player_name, "probability": p.probability, "weighted_probability": p.weighted_probability}
            for p in consensus.top_players
        ],
        "ml_top_players": ml_top,
        "org_adjusted_top_players": [
            {
                "player_name": p["player_name"],
                "position": p["position"],
                "org_adjusted_probability": p["org_adjusted_probability"],
                "organizational_component": p["organizational_component"],
            }
            for p in players["ranked_players"][:5]
        ],
        "top_position_predictions": pos["org_adjusted_position_probabilities"],
        "integrated_explanation": players["integrated_explanation"],
    }
    _write_team_view_cache(db, cycle.id, team.id, pick, summary_cache_key, payload)
    return payload


def _safe_json_list(raw: str) -> list[str]:
    try:
        value = json.loads(raw)
        if isinstance(value, list):
            return [str(v) for v in value]
    except json.JSONDecodeError:
        return []
    return []


def _organizational_component_for_position(position: str, priors: OrganizationalPriors) -> float:
    component = 0.5
    if position in {"OT", "IOL", "C", "G", "EDGE", "DT"}:
        component += (priors.trenches_prior - 0.5) * 0.9
    if position in {"WR", "RB", "TE", "CB", "S"}:
        component += (priors.skill_prior - 0.5) * 0.7
    if position in {"QB", "RB", "WR", "TE", "OT", "IOL", "C", "G"}:
        component += (priors.offense_prior - 0.5) * 0.6
    else:
        component += (priors.defense_prior - 0.5) * 0.6
    component += (priors.need_follow_prior - priors.bpa_deviation_prior) * 0.2
    return max(0.0, min(1.0, component))


def _build_integrated_explanation(
    team_abbr: str,
    top_position: str,
    top_player: str,
    priors: OrganizationalPriors,
    organizational_component: float,
) -> str:
    side = "offense" if priors.offense_prior >= priors.defense_prior else "defense"
    style = "need-aligned" if priors.need_follow_prior >= priors.bpa_deviation_prior else "BPA-leaning"
    stability_descriptor = (
        "stable regime" if priors.regime_stability_adjustment >= 0.6 else "transitional regime"
    )
    org_strength = "strongly" if organizational_component >= 0.62 else "moderately"
    return (
        f"{team_abbr} enters this pick as a {stability_descriptor} with a {side}-leaning, {style} front-office profile. "
        f"Need and board context surface {top_position}, while organizational priors {org_strength} reinforce "
        f"{top_player} as the preferred selection path."
    )


def _default_candidate_players(db: Session, cycle_id: int, year: int, pick: int) -> list[dict[str, object]]:
    prospects = db.scalars(
        select(ProspectFeature)
        .where(ProspectFeature.draft_cycle_id == cycle_id)
        .order_by(ProspectFeature.consensus_rank.asc().nulls_last())
        .limit(12)
    ).all()
    if prospects:
        payload: list[dict[str, object]] = []
        for idx, p in enumerate(prospects, start=1):
            payload.append(
                {
                    "player_id": p.player_id,
                    "player_name": p.full_name,
                    "position": p.position,
                    "prospect_score": float(p.production_score or p.market_score or 0.5),
                    "superstar_potential_score": float(p.superstar_potential_score or 0.5),
                    "consensus_rank": p.consensus_rank or idx,
                    "best_available_rank": 1,
                    "best_rank_in_position": p.positional_rank or 1,
                }
            )
        return payload

    consensus = pick_consensus(db, draft_year=year, overall_pick=pick, top_n=8)
    candidates: list[dict[str, object]] = []
    for idx, player in enumerate(consensus.top_players, start=1):
        candidates.append(
            {
                "player_name": player.player_name,
                "position": "UNK",
                "prospect_score": float(player.weighted_probability),
                "superstar_potential_score": float(player.weighted_probability),
                "consensus_rank": idx,
                "best_available_rank": 1,
                "best_rank_in_position": 1,
            }
        )
    return candidates


def _fallback_position_probs_from_needs(
    db: Session,
    cycle_id: int,
    team_id: int,
) -> dict[str, float]:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.id == cycle_id))
    if cycle is None:
        return {"OT": 0.2, "EDGE": 0.2, "CB": 0.2, "WR": 0.2, "QB": 0.2}
    raw = adjusted_need_map_for_team(db, team_id, cycle.year)
    if not raw:
        needs = db.scalars(
            select(TeamPositionNeedFeature).where(
                TeamPositionNeedFeature.draft_cycle_id == cycle_id,
                TeamPositionNeedFeature.team_id == team_id,
            )
        ).all()
        if not needs:
            return {"OT": 0.2, "EDGE": 0.2, "CB": 0.2, "WR": 0.2, "QB": 0.2}
        raw = {row.position: float(row.overall_need_score) for row in needs}
    total = sum(raw.values()) or 1.0
    return {k: v / total for k, v in sorted(raw.items(), key=lambda item: item[1], reverse=True)}


def _fallback_ranked_players(candidate_players: list[dict[str, object]]) -> list:
    class _FallbackPlayer:
        def __init__(self, row: dict[str, object], probability: float):
            self.player_name = str(row["player_name"])
            self.position = str(row["position"])
            self.probability = probability
            self.need_component = 0.5
            self.talent_component = float(row.get("prospect_score", 0.5))
            self.context_component = max(0.0, 1.0 - (float(row.get("consensus_rank") or 200) / 200.0))

    sorted_rows = sorted(candidate_players, key=lambda c: float(c.get("consensus_rank") or 300))
    scores = [max(0.01, 1.0 - (idx * 0.1)) for idx, _ in enumerate(sorted_rows)]
    total = sum(scores) or 1.0
    probs = [s / total for s in scores]
    return [_FallbackPlayer(row, prob) for row, prob in zip(sorted_rows, probs)]


def _team_current_pick_list(db: Session, cycle_id: int, team_id: int) -> list[int]:
    draft_order_rows = db.scalars(
        select(DraftOrderPick.overall_pick)
        .where(DraftOrderPick.draft_cycle_id == cycle_id, DraftOrderPick.team_id == team_id)
        .order_by(DraftOrderPick.overall_pick.asc())
    ).all()
    if draft_order_rows:
        return sorted({int(p) for p in draft_order_rows})

    picks = db.scalars(
        select(MockPick.overall_pick)
        .where(
            MockPick.draft_cycle_id == cycle_id,
            MockPick.current_team_id == team_id,
            MockPick.round_number == 1,
        )
        .order_by(MockPick.overall_pick.asc())
    ).all()
    return sorted({int(p) for p in picks})


def _candidate_signature(candidate_players: list[dict[str, object]]) -> str:
    canonical = json.dumps(
        [
            {
                "player_name": str(c.get("player_name", "")),
                "position": str(c.get("position", "")),
                "consensus_rank": c.get("consensus_rank"),
            }
            for c in sorted(candidate_players, key=lambda r: str(r.get("player_name", "")))
        ],
        sort_keys=True,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _read_team_view_cache(
    db: Session, cycle_id: int, team_id: int, overall_pick: int | None, model_version: str
) -> dict[str, object] | None:
    row = db.scalar(
        select(TeamViewPrediction).where(
            TeamViewPrediction.draft_cycle_id == cycle_id,
            TeamViewPrediction.team_id == team_id,
            TeamViewPrediction.overall_pick == overall_pick,
            TeamViewPrediction.model_version == model_version,
        )
    )
    if row is None:
        return None
    return json.loads(row.payload_json)


def _write_team_view_cache(
    db: Session, cycle_id: int, team_id: int, overall_pick: int | None, model_version: str, payload: dict[str, object]
) -> None:
    row = db.scalar(
        select(TeamViewPrediction).where(
            TeamViewPrediction.draft_cycle_id == cycle_id,
            TeamViewPrediction.team_id == team_id,
            TeamViewPrediction.overall_pick == overall_pick,
            TeamViewPrediction.model_version == model_version,
        )
    )
    if row is None:
        db.add(
            TeamViewPrediction(
                draft_cycle_id=cycle_id,
                team_id=team_id,
                overall_pick=overall_pick,
                model_version=model_version,
                payload_json=json.dumps(payload),
                generated_at=datetime.utcnow(),
            )
        )
    else:
        row.payload_json = json.dumps(payload)
        row.generated_at = datetime.utcnow()
    db.commit()


def run_org_backtest(
    base_prob_vectors: list[dict[str, float]],
    org_prob_vectors: list[dict[str, float]],
    consensus_prob_vectors: list[dict[str, float]],
    truths: list[str],
) -> dict[str, object]:
    ensemble = blend_consensus_ml_org(consensus_prob_vectors, org_prob_vectors)
    return {
        "train_window": [2014, 2020],
        "eval_window": [2021, 2025],
        "comparison": org_backtest_summary(
            base_prob_vectors=base_prob_vectors,
            org_prob_vectors=org_prob_vectors,
            ensemble_prob_vectors=ensemble,
            base_ranked=ranked_labels(base_prob_vectors),
            org_ranked=ranked_labels(org_prob_vectors),
            ensemble_ranked=ranked_labels(ensemble),
            truths=truths,
        ),
    }
