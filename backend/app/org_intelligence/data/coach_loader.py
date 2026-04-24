from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import CoachDraftContextFeature, DraftCycle, HeadCoach, TeamFrontOfficeHistory


@dataclass
class CoachProfileRow:
    coach_id: int
    coach_name: str
    years_of_prior_history: int
    offensive_background: bool | None
    defensive_background: bool | None
    prior_offense_pick_share: float
    prior_defense_pick_share: float
    prior_trenches_pick_share: float
    prior_skill_pick_share: float
    scheme_bias_label: str | None
    favored_positions_json: str | None


def load_coach_profile_for_team_year(db: Session, team_id: int, year: int) -> CoachProfileRow | None:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == year))
    if cycle is None:
        return None
    office = db.scalar(
        select(TeamFrontOfficeHistory).where(
            TeamFrontOfficeHistory.team_id == team_id,
            TeamFrontOfficeHistory.draft_cycle_id == cycle.id,
        )
    )
    if office is None or office.head_coach_id is None:
        return None
    coach = db.scalar(select(HeadCoach).where(HeadCoach.id == office.head_coach_id))
    feature = db.scalar(
        select(CoachDraftContextFeature).where(
            CoachDraftContextFeature.head_coach_id == office.head_coach_id,
            CoachDraftContextFeature.draft_cycle_id == cycle.id,
        )
    )
    if coach is None:
        return None
    if feature is None:
        return CoachProfileRow(
            coach_id=coach.id,
            coach_name=coach.full_name,
            years_of_prior_history=0,
            offensive_background=None,
            defensive_background=None,
            prior_offense_pick_share=0.5,
            prior_defense_pick_share=0.5,
            prior_trenches_pick_share=0.5,
            prior_skill_pick_share=0.5,
            scheme_bias_label=None,
            favored_positions_json=None,
        )
    return CoachProfileRow(
        coach_id=coach.id,
        coach_name=coach.full_name,
        years_of_prior_history=feature.years_of_prior_history,
        offensive_background=feature.offensive_background,
        defensive_background=feature.defensive_background,
        prior_offense_pick_share=float(feature.prior_offense_pick_share or 0),
        prior_defense_pick_share=float(feature.prior_defense_pick_share or 0),
        prior_trenches_pick_share=float(feature.prior_trenches_pick_share or 0),
        prior_skill_pick_share=float(feature.prior_skill_pick_share or 0),
        scheme_bias_label=feature.scheme_bias_label,
        favored_positions_json=feature.favored_positions_json,
    )
