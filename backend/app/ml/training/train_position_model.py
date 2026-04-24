import json
import pickle
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.entities import DraftCycle, MlModelRun, MockPick, PickContextFeature, TeamPositionNeedFeature
from backend.app.ml.models.position_model import PositionModel

ARTIFACT_DIR = Path("backend/artifacts/ml")


def train_position_model(
    train_start: int = 2014,
    train_end: int = 2020,
    validation_start: int = 2021,
    validation_end: int = 2022,
    test_start: int = 2023,
    test_end: int = 2025,
) -> str:
    with SessionLocal() as db:
        train_rows = _build_training_rows(db, train_start, train_end)
        if not train_rows:
            raise ValueError("No rows found for training position model")
        model = PositionModel()
        bundle = model.train(train_rows)

        artifact_path = ARTIFACT_DIR / f"position_model_{bundle.version}.pkl"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        with artifact_path.open("wb") as handle:
            pickle.dump(bundle, handle)

        db.add(
            MlModelRun(
                model_family="position_model",
                model_version=bundle.version,
                train_year_start=train_start,
                train_year_end=train_end,
                validation_year_start=validation_start,
                validation_year_end=validation_end,
                test_year_start=test_start,
                test_year_end=test_end,
                metrics_json=json.dumps({"train_rows": len(train_rows)}),
                artifact_path=str(artifact_path),
            )
        )
        db.commit()
        return bundle.version


def _build_training_rows(db: Session, year_start: int, year_end: int) -> list[dict[str, float | str | int]]:
    cycles = db.scalars(
        select(DraftCycle).where(DraftCycle.year >= year_start, DraftCycle.year <= year_end)
    ).all()
    cycle_ids = [c.id for c in cycles]
    if not cycle_ids:
        return []

    need_rows = db.scalars(
        select(TeamPositionNeedFeature).where(TeamPositionNeedFeature.draft_cycle_id.in_(cycle_ids))
    ).all()
    need_map = {(r.draft_cycle_id, r.team_id, r.position): float(r.overall_need_score) for r in need_rows}

    ctx_rows = db.scalars(
        select(PickContextFeature).where(PickContextFeature.draft_cycle_id.in_(cycle_ids))
    ).all()
    ctx_map = {(r.draft_cycle_id, r.team_id, r.overall_pick): r for r in ctx_rows}

    picks = db.scalars(select(MockPick).where(MockPick.draft_cycle_id.in_(cycle_ids))).all()
    records: list[dict[str, float | str | int]] = []
    for pick in picks:
        if pick.current_team_id is None or pick.normalized_position is None:
            continue
        ctx = ctx_map.get((pick.draft_cycle_id, pick.current_team_id, pick.overall_pick))
        if ctx is None:
            continue
        need_score = need_map.get(
            (pick.draft_cycle_id, pick.current_team_id, pick.normalized_position),
            0.5,
        )
        records.append(
            {
                "need_score": need_score,
                "board_scarcity_score": float(ctx.board_scarcity_score or 0),
                "best_available_player_score": float(ctx.best_available_player_score or 0),
                "overall_pick": pick.overall_pick,
                "round_number": pick.round_number,
                "top_need_position": ctx.top_need_position or "UNK",
                "label_position": pick.normalized_position,
            }
        )
    return records
