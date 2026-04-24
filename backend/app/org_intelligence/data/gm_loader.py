from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import DraftCycle, GeneralManager, GmDraftHistoryFeature, TeamFrontOfficeHistory


@dataclass
class GmProfileRow:
    gm_id: int
    gm_name: str
    years_of_prior_draft_history: int
    offense_share: float
    defense_share: float
    trenches_share: float
    skill_share: float
    need_follow_rate: float
    bpa_proxy_rate: float
    favored_positions_json: str | None


def load_gm_profile_for_team_year(db: Session, team_id: int, year: int) -> GmProfileRow | None:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if cycle is None:
        return None
    office = db.scalar(
        select(TeamFrontOfficeHistory).where(
            TeamFrontOfficeHistory.team_id == team_id,
            TeamFrontOfficeHistory.draft_cycle_id == cycle.id,
        )
    )
    if office is None or office.general_manager_id is None:
        return None
    gm = db.scalar(select(GeneralManager).where(GeneralManager.id == office.general_manager_id))
    feature = db.scalar(
        select(GmDraftHistoryFeature).where(
            GmDraftHistoryFeature.general_manager_id == office.general_manager_id,
            GmDraftHistoryFeature.draft_cycle_id == cycle.id,
        )
    )
    if gm is None:
        return None
    if feature is None:
        return GmProfileRow(
            gm_id=gm.id,
            gm_name=gm.full_name,
            years_of_prior_draft_history=0,
            offense_share=0.5,
            defense_share=0.5,
            trenches_share=0.5,
            skill_share=0.5,
            need_follow_rate=0.5,
            bpa_proxy_rate=0.5,
            favored_positions_json=None,
        )
    return GmProfileRow(
        gm_id=gm.id,
        gm_name=gm.full_name,
        years_of_prior_draft_history=feature.years_of_prior_draft_history,
        offense_share=float(feature.avg_pick_value_spent_offense or 0),
        defense_share=float(feature.avg_pick_value_spent_defense or 0),
        trenches_share=float(feature.pct_first_round_trenches or 0),
        skill_share=float(feature.pct_first_round_skill or 0),
        need_follow_rate=float(feature.pct_picks_same_side_as_top_need or 0),
        bpa_proxy_rate=float(feature.pct_picks_best_player_available_proxy or 0),
        favored_positions_json=feature.favored_positions_json,
    )
