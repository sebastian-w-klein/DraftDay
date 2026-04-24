import json
from pathlib import Path

from app.db.session import SessionLocal
from app.models.entities import MlModelRun

ARTIFACT_DIR = Path("backend/artifacts/org_intelligence")


def train_org_prior_model(train_start: int = 2014, train_end: int = 2020) -> str:
    version = "org-prior-v1"
    artifact_path = ARTIFACT_DIR / f"org_prior_{version}.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps({"version": version, "train_window": [train_start, train_end]}, indent=2), encoding="utf-8")
    with SessionLocal() as db:
        db.add(
            MlModelRun(
                model_family="org_prior_model",
                model_version=version,
                train_year_start=train_start,
                train_year_end=train_end,
                validation_year_start=None,
                validation_year_end=None,
                test_year_start=None,
                test_year_end=None,
                metrics_json=json.dumps({"status": "heuristic priors"}),
                artifact_path=str(artifact_path),
            )
        )
        db.commit()
    return version
