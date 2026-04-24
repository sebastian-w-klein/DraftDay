import json
import pickle
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import CandidatePlayerFeature, DraftCycle, MlModelRun
from backend.app.ml.models.player_model import PlayerModel

ARTIFACT_DIR = Path("backend/artifacts/ml")


def train_player_model(
    train_start: int = 2014,
    train_end: int = 2020,
    validation_start: int = 2021,
    validation_end: int = 2022,
    test_start: int = 2023,
    test_end: int = 2025,
) -> str:
    with SessionLocal() as db:
        cycles = db.scalars(
            select(DraftCycle).where(DraftCycle.year >= train_start, DraftCycle.year <= train_end)
        ).all()
        cycle_ids = [c.id for c in cycles]
        rows = db.scalars(
            select(CandidatePlayerFeature).where(CandidatePlayerFeature.draft_cycle_id.in_(cycle_ids))
        ).all()
        payload = [
            {
                "candidate_player_id": row.candidate_player_id,
                "candidate_player_name": row.candidate_player_name,
                "position": row.position,
                "team_need_score": float(row.team_need_score),
                "prospect_score": float(row.prospect_score),
                "superstar_potential_score": float(row.superstar_potential_score),
                "consensus_rank": row.consensus_rank,
                "rank_gap_from_best_available": float(row.rank_gap_from_best_available or 0),
                "rank_gap_within_position": float(row.rank_gap_within_position or 0),
                "positional_scarcity_score": float(row.positional_scarcity_score or 0),
                "fit_gap": abs(float(row.team_need_score) - float(row.prospect_score)),
                "need_vs_bpa_gap": float(row.team_need_score) - float(row.prospect_score),
                "selected_label": bool(row.selected_label),
            }
            for row in rows
        ]
        model = PlayerModel()
        bundle = model.train(payload)
        artifact_path = ARTIFACT_DIR / f"player_model_{bundle.version}.pkl"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        with artifact_path.open("wb") as handle:
            pickle.dump(bundle, handle)

        db.add(
            MlModelRun(
                model_family="player_model",
                model_version=bundle.version,
                train_year_start=train_start,
                train_year_end=train_end,
                validation_year_start=validation_start,
                validation_year_end=validation_end,
                test_year_start=test_start,
                test_year_end=test_end,
                metrics_json=json.dumps({"train_rows": len(payload)}),
                artifact_path=str(artifact_path),
            )
        )
        db.commit()
        return bundle.version
