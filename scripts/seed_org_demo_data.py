import json
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.models.entities import (  # noqa: E402
    CoachDraftContextFeature,
    DraftCycle,
    GeneralManager,
    GmDraftHistoryFeature,
    HeadCoach,
    Team,
    TeamFrontOfficeHistory,
    TeamOrgTendencyFeature,
)
from app.normalization.normalizers import normalize_player_name  # noqa: E402


def _get_or_create_gm(db, full_name: str) -> GeneralManager:
    normalized = normalize_player_name(full_name)
    gm = db.scalar(select(GeneralManager).where(GeneralManager.normalized_name == normalized))
    if gm is None:
        gm = GeneralManager(full_name=full_name, normalized_name=normalized)
        db.add(gm)
        db.flush()
    return gm


def _get_or_create_hc(db, full_name: str) -> HeadCoach:
    normalized = normalize_player_name(full_name)
    hc = db.scalar(select(HeadCoach).where(HeadCoach.normalized_name == normalized))
    if hc is None:
        hc = HeadCoach(full_name=full_name, normalized_name=normalized)
        db.add(hc)
        db.flush()
    return hc


def main() -> None:
    with SessionLocal() as db:
        target_year = datetime.utcnow().year
        cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == target_year))
        team = db.scalar(select(Team).where(Team.abbreviation == "TEN"))
        if cycle is None or team is None:
            print(f"Missing TEN team or {target_year} cycle. Run bootstrap_demo_data first.")
            return

        gm = _get_or_create_gm(db, "Ran Carthon")
        hc = _get_or_create_hc(db, "Brian Callahan")

        office = db.scalar(
            select(TeamFrontOfficeHistory).where(
                TeamFrontOfficeHistory.draft_cycle_id == cycle.id,
                TeamFrontOfficeHistory.team_id == team.id,
            )
        )
        if office is None:
            office = TeamFrontOfficeHistory(
                draft_cycle_id=cycle.id,
                team_id=team.id,
                general_manager_id=gm.id,
                head_coach_id=hc.id,
                gm_tenure_year=3,
                hc_tenure_year=2,
                control_regime_label="gm_hc_active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(office)
        else:
            office.general_manager_id = gm.id
            office.head_coach_id = hc.id
            office.gm_tenure_year = 3
            office.hc_tenure_year = 2
            office.control_regime_label = "gm_hc_active"
            office.updated_at = datetime.utcnow()

        gm_feat = db.scalar(
            select(GmDraftHistoryFeature).where(
                GmDraftHistoryFeature.general_manager_id == gm.id,
                GmDraftHistoryFeature.draft_cycle_id == cycle.id,
            )
        )
        if gm_feat is None:
            gm_feat = GmDraftHistoryFeature(
                general_manager_id=gm.id,
                draft_cycle_id=cycle.id,
                years_of_prior_draft_history=3,
                total_prior_picks=24,
                avg_pick_value_spent_offense=0.58,
                avg_pick_value_spent_defense=0.42,
                pct_first_round_trenches=0.63,
                pct_first_round_skill=0.37,
                pct_picks_same_side_as_top_need=0.67,
                pct_picks_best_player_available_proxy=0.49,
                pct_early_round_trades_up=0.21,
                pct_early_round_trades_down=0.12,
                avg_positional_value_of_picks=0.61,
                favored_positions_json=json.dumps(["OT", "EDGE", "CB"]),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(gm_feat)

        coach_feat = db.scalar(
            select(CoachDraftContextFeature).where(
                CoachDraftContextFeature.head_coach_id == hc.id,
                CoachDraftContextFeature.draft_cycle_id == cycle.id,
            )
        )
        if coach_feat is None:
            coach_feat = CoachDraftContextFeature(
                head_coach_id=hc.id,
                draft_cycle_id=cycle.id,
                years_of_prior_history=2,
                offensive_background=True,
                defensive_background=False,
                prior_offense_pick_share=0.56,
                prior_defense_pick_share=0.44,
                prior_trenches_pick_share=0.51,
                prior_skill_pick_share=0.49,
                favored_positions_json=json.dumps(["QB", "WR", "OT"]),
                scheme_bias_label="offense",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(coach_feat)

        tendency = db.scalar(
            select(TeamOrgTendencyFeature).where(
                TeamOrgTendencyFeature.draft_cycle_id == cycle.id,
                TeamOrgTendencyFeature.team_id == team.id,
            )
        )
        if tendency is None:
            tendency = TeamOrgTendencyFeature(
                draft_cycle_id=cycle.id,
                team_id=team.id,
                general_manager_id=gm.id,
                head_coach_id=hc.id,
                organization_regime_key=f"TEN_{target_year}_Ran_Brian",
                recent_offense_pick_share=0.57,
                recent_defense_pick_share=0.43,
                recent_trenches_pick_share=0.62,
                recent_skill_pick_share=0.38,
                recent_need_follow_rate=0.68,
                recent_bpa_deviation_rate=0.32,
                recent_early_round_positional_concentration=0.64,
                recent_pick_volatility=0.28,
                regime_stability_score=0.73,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(tendency)
        else:
            tendency.general_manager_id = gm.id
            tendency.head_coach_id = hc.id
            tendency.recent_offense_pick_share = 0.57
            tendency.recent_defense_pick_share = 0.43
            tendency.recent_trenches_pick_share = 0.62
            tendency.recent_skill_pick_share = 0.38
            tendency.recent_need_follow_rate = 0.68
            tendency.recent_bpa_deviation_rate = 0.32
            tendency.recent_early_round_positional_concentration = 0.64
            tendency.recent_pick_volatility = 0.28
            tendency.regime_stability_score = 0.73
            tendency.updated_at = datetime.utcnow()

        db.commit()
    print(f"Seeded org-intelligence demo data for TEN {target_year}.")


if __name__ == "__main__":
    main()
