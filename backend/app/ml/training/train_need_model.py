import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import DraftCycle, MlModelRun, TeamPositionNeedFeature
from backend.app.ml.data.roster_loader import load_roster_rows
from backend.app.ml.features.need_features import build_need_features
from backend.app.ml.models.need_model import HeuristicNeedModel

ARTIFACT_DIR = Path("backend/artifacts/ml")


def train_need_model_for_year(year: int) -> str:
    model = HeuristicNeedModel()
    with SessionLocal() as db:
        roster_rows = load_roster_rows(db, year)
        feature_rows = build_need_features(roster_rows)
        scores = model.score(feature_rows)
        cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
        if cycle is None:
            raise ValueError(f"Unknown draft year: {year}")

        if scores:
            db.query(TeamPositionNeedFeature).filter(
                TeamPositionNeedFeature.draft_cycle_id == cycle.id
            ).delete()
            for score in scores:
                db.add(
                    TeamPositionNeedFeature(
                        draft_cycle_id=cycle.id,
                        team_id=score.team_id,
                        position=score.position,
                        returning_snaps=score.feature_summary["snaps_risk"],
                        returning_starts=score.feature_summary["starts_risk"],
                        avg_age=score.feature_summary["age_risk"],
                        avg_experience=score.feature_summary["experience_risk"],
                        depth_count=score.feature_summary["depth_risk"],
                        starter_continuity=1 - score.feature_summary["continuity_risk"],
                        recent_draft_investment=None,
                        recent_free_agent_investment=None,
                        short_term_need_score=score.short_term_need_score,
                        long_term_need_score=score.long_term_need_score,
                        overall_need_score=score.overall_need_score,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )

        version = f"{model.version}-{year}"
        artifact_path = ARTIFACT_DIR / f"need_model_{year}.json"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            json.dumps({"model_version": version, "scored_positions": len(scores)}, indent=2),
            encoding="utf-8",
        )
        db.add(
            MlModelRun(
                model_family="need_model",
                model_version=version,
                train_year_start=year,
                train_year_end=year,
                validation_year_start=None,
                validation_year_end=None,
                test_year_start=None,
                test_year_end=None,
                metrics_json=json.dumps({"rows": len(scores)}),
                artifact_path=str(artifact_path),
            )
        )
        db.commit()
    return version
