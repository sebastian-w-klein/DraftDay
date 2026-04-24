import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.models.entities import DraftCycle, ProspectFeature, TeamPositionNeedFeature  # noqa: E402
from backend.app.ml.training.train_need_model import train_need_model_for_year  # noqa: E402
from backend.app.ml.training.train_player_model import train_player_model  # noqa: E402
from backend.app.ml.training.train_position_model import train_position_model  # noqa: E402
from backend.app.org_intelligence.training.train_integrated_team_model import (  # noqa: E402
    train_integrated_team_model,
)
from backend.app.org_intelligence.training.train_org_prior_model import train_org_prior_model  # noqa: E402


def main() -> None:
    with SessionLocal() as db:
        years = db.scalars(select(DraftCycle.year).order_by(DraftCycle.year.asc())).all()
        rich_cycle_ids = db.scalars(
            select(DraftCycle.id)
            .join(ProspectFeature, ProspectFeature.draft_cycle_id == DraftCycle.id)
            .join(TeamPositionNeedFeature, TeamPositionNeedFeature.draft_cycle_id == DraftCycle.id)
            .distinct()
        ).all()
        rich_years = db.scalars(select(DraftCycle.year).where(DraftCycle.id.in_(rich_cycle_ids))).all() if rich_cycle_ids else []
    if not years:
        print("No draft cycles found. Seed draft cycles first.")
        return

    current_year = max(rich_years) if rich_years else max(years)
    train_start = min(years)
    train_end = current_year
    validation_start = current_year
    validation_end = current_year
    test_start = current_year
    test_end = current_year

    trained: list[str] = []
    try:
        trained.append(f"need:{train_need_model_for_year(current_year)}")
    except Exception as exc:  # noqa: BLE001
        print(f"Need model training skipped/failed: {exc}")

    try:
        trained.append(
            "position:"
            + train_position_model(
                train_start=train_start,
                train_end=train_end,
                validation_start=validation_start,
                validation_end=validation_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Position model training skipped/failed: {exc}")

    try:
        trained.append(
            "player:"
            + train_player_model(
                train_start=train_start,
                train_end=train_end,
                validation_start=validation_start,
                validation_end=validation_end,
                test_start=test_start,
                test_end=test_end,
            )
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Player model training skipped/failed: {exc}")

    try:
        trained.append(f"org_prior:{train_org_prior_model(train_start=train_start, train_end=train_end)}")
    except Exception as exc:  # noqa: BLE001
        print(f"Org prior training skipped/failed: {exc}")

    try:
        trained.append(
            f"integrated_team:{train_integrated_team_model(train_start=train_start, train_end=train_end)}"
        )
    except Exception as exc:  # noqa: BLE001
        print(f"Integrated team training skipped/failed: {exc}")

    print("Training run complete.")
    print("Trained model runs:")
    for item in trained:
        print(f" - {item}")


if __name__ == "__main__":
    main()
