import numpy as np
import pandas as pd
import pytest

pytest.importorskip("pandas")

from backend.app.draft_slot.college_production import (  # noqa: E402
    add_rates,
    aggregate_season,
    normalize_name,
    summarize_prospect,
)
from backend.app.draft_slot.dataset import normalize_school  # noqa: E402
from backend.app.draft_slot.design import apply_design, fit_design  # noqa: E402
from backend.app.draft_slot.features import add_features, assign_position_group  # noqa: E402


def test_normalize_name_strips_suffixes_and_punctuation() -> None:
    assert normalize_name("Ja'Marr Chase") == "jamarr chase"
    assert normalize_name("Carlos Basham Jr.") == "carlos basham"
    assert normalize_name("Amon-Ra St. Brown") == "amon ra st brown"


def test_normalize_school_handles_combine_spellings() -> None:
    assert normalize_school("Ohio St.") == normalize_school("Ohio State")
    assert normalize_school("Mississippi") == "ole miss"
    assert normalize_school("West. Michigan") == "western michigan"
    assert normalize_school("San José State") == "san jose state"
    assert normalize_school("Middle Tenn. St.") == "middle tennessee"


def test_assign_position_group_splits_by_weight() -> None:
    assert assign_position_group("OLB", 255) == "EDGE"
    assert assign_position_group("OLB", 230) == "LB"
    assert assign_position_group("DE", 300) == "IDL"
    assert assign_position_group("OG", 315) == "IOL"
    assert assign_position_group("K", 190) is None


def _play(**kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {
        "game_id": 1,
        "season": 2020,
        "team": "A",
        "conference": "SEC",
        "opponent": "B",
    }
    cols = [
        "reception_player_id",
        "reception_player",
        "reception_yds",
        "completion_player_id",
        "completion_player",
        "completion_yds",
        "rush_player_id",
        "rush_player",
        "rush_yds",
        "interception_player_id",
        "interception_player",
        "interception_thrown_player_id",
        "touchdown_player_id",
        "incompletion_player_id",
        "target_player_id",
        "target_player",
        "fumble_forced_player_id",
        "fumble_forced_player",
        "sack_player_id",
        "sack_player",
        "sack_taken_player_id",
        "pass_breakup_player_id",
        "pass_breakup_player",
    ]
    base.update({c: np.nan for c in cols})
    base.update(kwargs)
    return base


def test_aggregate_season_attributes_touchdowns_and_teams() -> None:
    plays = pd.DataFrame(
        [
            # Completed TD where the feed credits the passer as touchdown_player.
            _play(
                completion_player_id=10,
                completion_player="QB One",
                completion_yds=20,
                reception_player_id=20,
                reception_player="WR One",
                reception_yds=20,
                touchdown_player_id=10,
            ),
            _play(
                completion_player_id=10,
                completion_player="QB One",
                completion_yds=10,
                reception_player_id=21,
                reception_player="WR Two",
                reception_yds=10,
            ),
            _play(incompletion_player_id=10, target_player_id=20, target_player="WR One"),
            _play(rush_player_id=30, rush_player="RB One", rush_yds=5, touchdown_player_id=30),
            # Interception: the feed lists the defense as ``team`` on turnovers.
            _play(
                team="B",
                opponent="A",
                interception_thrown_player_id=10,
                interception_player_id=40,
                interception_player="DB B",
            ),
            # Sack by a B defender while A has the ball.
            _play(sack_taken_player_id=10, sack_player_id=41, sack_player="DE B"),
            # B's offense in a second game so B's players have their own plays.
            _play(
                game_id=2, team="B", opponent="C", rush_player_id=42, rush_player="RB B", rush_yds=3
            ),
            _play(
                game_id=2, team="B", opponent="C", rush_player_id=42, rush_player="RB B", rush_yds=4
            ),
        ]
    )
    season = aggregate_season(plays).set_index("athlete_id")
    assert season.loc[10, "pass_td"] == 1
    assert season.loc[10, "pass_int"] == 1
    assert season.loc[10, "pass_inc"] == 1
    assert season.loc[20, "rec_td"] == 1
    assert season.loc[20, "incomplete_targets"] == 1
    assert season.loc[30, "rush_td"] == 1
    assert season.loc[40, "def_int"] == 1
    assert season.loc[41, "def_sacks"] == 1
    assert season.loc[10, "team"] == "A"
    assert season.loc[42, "team"] == "B"
    rates = add_rates(season.reset_index()).set_index("athlete_id")
    assert rates.loc[20, "rec_yds_share"] == pytest.approx(20 / 30)
    assert rates.loc[10, "pass_att"] == 4  # 2 completions + 1 incompletion + 1 INT


def test_summarize_prospect_uses_only_pre_draft_seasons() -> None:
    rows = []
    for season, share in [(2018, 0.10), (2019, 0.25), (2020, 0.30)]:
        rows.append(
            {
                "season": season,
                "games": 12,
                "team_games": 12,
                "rec_yds": share * 1000,
                "team_rec_yds": 1000,
                "rec": 50,
                "incomplete_targets": 20,
                "rec_td": 5,
                "team_rec_td": 20,
            }
        )
    seasons = pd.DataFrame(rows).reindex(
        columns=[
            "season",
            "games",
            "team_games",
            "rec_yds",
            "team_rec_yds",
            "rec",
            "incomplete_targets",
            "rec_td",
            "team_rec_td",
            "pass_cmp",
            "pass_inc",
            "pass_int",
            "pass_yds",
            "pass_td",
            "sacks_taken",
            "rush_att",
            "rush_yds",
            "rush_td",
            "def_sacks",
            "def_int",
            "def_pbu",
            "def_ff",
            "team_pass_yds",
            "team_rush_att",
            "team_rush_yds",
            "team_rec",
            "team_rush_td",
            "team_def_sacks",
            "team_def_int",
            "team_def_pbu",
        ],
        fill_value=0,
    )
    summary = summarize_prospect(add_rates(seasons), draft_year=2020)
    assert summary["final_rec_yds_share"] == pytest.approx(0.25)
    assert summary["college_seasons"] == 2
    assert summary["breakout_season"] == 2019


def _combine_rows() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 40
    return pd.DataFrame(
        {
            "pos": ["WR"] * n,
            "height_in": rng.normal(73, 2, n),
            "weight_lb": rng.normal(200, 10, n),
            "forty": np.where(np.arange(n) % 5 == 0, np.nan, rng.normal(4.5, 0.08, n)),
            "bench": rng.normal(14, 4, n),
            "vertical": rng.normal(35, 3, n),
            "broad": rng.normal(122, 5, n),
            "cone": rng.normal(6.9, 0.2, n),
            "shuttle": rng.normal(4.2, 0.1, n),
            "overall_pick": np.where(np.arange(n) % 3 == 0, np.nan, rng.integers(1, 250, n)),
            "draft_year": 2020,
        }
    )


def test_add_features_orients_times_and_flags_skips() -> None:
    df = add_features(_combine_rows())
    fastest = df.loc[df["forty"].idxmin()]
    assert fastest["z_forty"] == df["z_forty"].max()
    assert df.loc[df["forty"].isna(), "forty_missing"].eq(1).all()
    assert df.loc[df["overall_pick"].isna(), "pick_or_undrafted"].eq(300).all()


def test_design_spec_replays_on_new_rows() -> None:
    df = add_features(_combine_rows())
    features = ["z_height_in", "z_forty", "forty_missing", "agility_missing", "age_at_draft"]
    df["age_at_draft"] = np.where(np.arange(len(df)) % 4 == 0, np.nan, 22.0 + df.index % 3)
    X, spec = fit_design(df, features)
    replay = apply_design(df, spec)
    pd.testing.assert_frame_equal(X, replay[X.columns])
    assert "age_at_draft_na" in X.columns
    assert X["z_forty"].mean() == pytest.approx(0.0, abs=1e-9)


def test_age_is_excluded_from_targets_that_include_undrafted() -> None:
    pytest.importorskip("statsmodels")
    from backend.app.draft_slot.analysis import features_for_target, model_features

    feats = model_features("WR", with_production=False)
    assert "age_at_draft" in features_for_target(feats, "log_pick")
    assert "age_at_draft" not in features_for_target(feats, "drafted")
    assert "age_at_draft" not in features_for_target(feats, "draft_capital")
    assert "z_bench" not in model_features("QB", with_production=False)
    assert "fbs" not in model_features("WR", with_production=True)


def test_score_prospects_applies_exported_prior() -> None:
    from backend.app.draft_slot.priors import score_prospects

    df = add_features(_combine_rows())
    _, spec = fit_design(df, ["z_forty"])
    priors = {
        "athletic": {
            "WR": {
                "target": "draft_capital",
                "intercept": 0.0,
                "draft_year_coef": 0.0,
                "coefficients": {"z_forty": {"coef": 1.0, "p_value": 0.001}},
                "spec": spec.to_dict(),
            }
        }
    }
    scored = score_prospects(df, priors, variant="athletic")
    ran = scored[scored["forty_missing"] == 0]
    assert ran.loc[ran["forty"].idxmin(), "prior_score"] == ran["prior_score"].max()
    zeroed = score_prospects(df, priors, variant="athletic", max_p_value=0.0001)
    assert zeroed["prior_score"].eq(0).all()
