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

TEAM_ROWS = [
    ("ARI", "Arizona Cardinals", "Arizona"),
    ("ATL", "Atlanta Falcons", "Atlanta"),
    ("BAL", "Baltimore Ravens", "Baltimore"),
    ("BUF", "Buffalo Bills", "Buffalo"),
    ("CAR", "Carolina Panthers", "Carolina"),
    ("CHI", "Chicago Bears", "Chicago"),
    ("CIN", "Cincinnati Bengals", "Cincinnati"),
    ("CLE", "Cleveland Browns", "Cleveland"),
    ("DAL", "Dallas Cowboys", "Dallas"),
    ("DEN", "Denver Broncos", "Denver"),
    ("DET", "Detroit Lions", "Detroit"),
    ("GB", "Green Bay Packers", "Green Bay"),
    ("HOU", "Houston Texans", "Houston"),
    ("IND", "Indianapolis Colts", "Indianapolis"),
    ("JAX", "Jacksonville Jaguars", "Jacksonville"),
    ("KC", "Kansas City Chiefs", "Kansas City"),
    ("LAC", "Los Angeles Chargers", "Los Angeles"),
    ("LAR", "Los Angeles Rams", "Los Angeles"),
    ("LV", "Las Vegas Raiders", "Las Vegas"),
    ("MIA", "Miami Dolphins", "Miami"),
    ("MIN", "Minnesota Vikings", "Minnesota"),
    ("NE", "New England Patriots", "New England"),
    ("NO", "New Orleans Saints", "New Orleans"),
    ("NYG", "New York Giants", "New York"),
    ("NYJ", "New York Jets", "New York"),
    ("PHI", "Philadelphia Eagles", "Philadelphia"),
    ("PIT", "Pittsburgh Steelers", "Pittsburgh"),
    ("SEA", "Seattle Seahawks", "Seattle"),
    ("SF", "San Francisco 49ers", "San Francisco"),
    ("TB", "Tampa Bay Buccaneers", "Tampa Bay"),
    ("TEN", "Tennessee Titans", "Tennessee"),
    ("WAS", "Washington Commanders", "Washington"),
]


def _upsert_teams(db) -> None:
    for abbr, full_name, city in TEAM_ROWS:
        team = db.scalar(select(Team).where(Team.abbreviation == abbr))
        if team is None:
            db.add(Team(abbreviation=abbr, full_name=full_name, city=city, conference=None, division=None, active=True))


def _get_or_create_gm(db, name: str) -> GeneralManager:
    norm = normalize_player_name(name)
    row = db.scalar(select(GeneralManager).where(GeneralManager.normalized_name == norm))
    if row is None:
        row = GeneralManager(full_name=name, normalized_name=norm, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        db.add(row)
        db.flush()
    return row


def _get_or_create_hc(db, name: str) -> HeadCoach:
    norm = normalize_player_name(name)
    row = db.scalar(select(HeadCoach).where(HeadCoach.normalized_name == norm))
    if row is None:
        row = HeadCoach(full_name=name, normalized_name=norm, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        db.add(row)
        db.flush()
    return row


def _score(seed: int, low: float, high: float) -> float:
    return low + ((seed % 100) / 100.0) * (high - low)


def main() -> None:
    target_year = datetime.utcnow().year
    with SessionLocal() as db:
        cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == target_year))
        if cycle is None:
            print(f"Draft cycle {target_year} not found.")
            return
        _upsert_teams(db)
        db.flush()
        teams = db.scalars(select(Team).where(Team.active == True)).all()  # noqa: E712
        count = 0
        for team in teams:
            seed = sum(ord(c) for c in team.abbreviation)
            gm = _get_or_create_gm(db, f"{team.abbreviation} GM")
            hc = _get_or_create_hc(db, f"{team.abbreviation} HC")

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
                    gm_tenure_year=2,
                    hc_tenure_year=2,
                    control_regime_label="baseline-regime",
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(office)

            gmf = db.scalar(
                select(GmDraftHistoryFeature).where(
                    GmDraftHistoryFeature.general_manager_id == gm.id,
                    GmDraftHistoryFeature.draft_cycle_id == cycle.id,
                )
            )
            if gmf is None:
                db.add(
                    GmDraftHistoryFeature(
                        general_manager_id=gm.id,
                        draft_cycle_id=cycle.id,
                        years_of_prior_draft_history=2,
                        total_prior_picks=14,
                        avg_pick_value_spent_offense=_score(seed, 0.45, 0.60),
                        avg_pick_value_spent_defense=_score(seed + 3, 0.40, 0.55),
                        pct_first_round_trenches=_score(seed + 7, 0.42, 0.68),
                        pct_first_round_skill=_score(seed + 11, 0.32, 0.58),
                        pct_picks_same_side_as_top_need=_score(seed + 13, 0.50, 0.72),
                        pct_picks_best_player_available_proxy=_score(seed + 17, 0.30, 0.55),
                        pct_early_round_trades_up=_score(seed + 19, 0.05, 0.20),
                        pct_early_round_trades_down=_score(seed + 23, 0.05, 0.18),
                        avg_positional_value_of_picks=_score(seed + 29, 0.45, 0.70),
                        favored_positions_json=json.dumps(["OT", "EDGE", "CB"]),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )

            cdf = db.scalar(
                select(CoachDraftContextFeature).where(
                    CoachDraftContextFeature.head_coach_id == hc.id,
                    CoachDraftContextFeature.draft_cycle_id == cycle.id,
                )
            )
            if cdf is None:
                offense_bias = (seed % 2) == 0
                db.add(
                    CoachDraftContextFeature(
                        head_coach_id=hc.id,
                        draft_cycle_id=cycle.id,
                        years_of_prior_history=2,
                        offensive_background=offense_bias,
                        defensive_background=not offense_bias,
                        prior_offense_pick_share=_score(seed + 31, 0.42, 0.58),
                        prior_defense_pick_share=_score(seed + 37, 0.42, 0.58),
                        prior_trenches_pick_share=_score(seed + 41, 0.40, 0.62),
                        prior_skill_pick_share=_score(seed + 43, 0.38, 0.60),
                        favored_positions_json=json.dumps(["WR", "OT", "CB"]),
                        scheme_bias_label="offense" if offense_bias else "defense",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )

            tof = db.scalar(
                select(TeamOrgTendencyFeature).where(
                    TeamOrgTendencyFeature.draft_cycle_id == cycle.id,
                    TeamOrgTendencyFeature.team_id == team.id,
                )
            )
            if tof is None:
                db.add(
                    TeamOrgTendencyFeature(
                        draft_cycle_id=cycle.id,
                        team_id=team.id,
                        general_manager_id=gm.id,
                        head_coach_id=hc.id,
                        organization_regime_key=f"{team.abbreviation}_{target_year}_baseline",
                        recent_offense_pick_share=_score(seed + 47, 0.42, 0.60),
                        recent_defense_pick_share=_score(seed + 53, 0.40, 0.58),
                        recent_trenches_pick_share=_score(seed + 59, 0.42, 0.66),
                        recent_skill_pick_share=_score(seed + 61, 0.34, 0.58),
                        recent_need_follow_rate=_score(seed + 67, 0.50, 0.72),
                        recent_bpa_deviation_rate=_score(seed + 71, 0.28, 0.50),
                        recent_early_round_positional_concentration=_score(seed + 73, 0.45, 0.70),
                        recent_pick_volatility=_score(seed + 79, 0.20, 0.45),
                        regime_stability_score=_score(seed + 83, 0.55, 0.80),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
            count += 1

        db.commit()
    print(f"Seeded baseline org profiles for {count} teams in {target_year}.")


if __name__ == "__main__":
    main()
