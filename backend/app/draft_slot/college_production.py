"""Aggregate cfbfastR play-level player stats into player-season production.

The play-level feed does not cover every game (roughly 70-85% of FBS games per
season), so raw season totals undercount. Rates (per game, per attempt) and
shares of the team's production in covered games are robust to that and are
what the analysis relies on.

Offensive rates use the games a player appears in; defensive rates use the
team's covered games, since defenders only show up in the feed when they record
a stat.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

_SUFFIX_RE = re.compile(r"\b(jr|sr|ii|iii|iv|v)\b")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9 ]+")


def normalize_name(name: object) -> str:
    if not isinstance(name, str):
        return ""
    value = name.lower().replace("'", "").replace(".", "").replace("-", " ")
    value = _NON_ALNUM_RE.sub(" ", value)
    value = _SUFFIX_RE.sub(" ", value)
    return " ".join(value.split())


_ID_NAME_COLUMNS = [
    ("completion_player_id", "completion_player"),
    ("incompletion_player_id", None),
    ("interception_thrown_player_id", None),
    ("sack_taken_player_id", None),
    ("rush_player_id", "rush_player"),
    ("reception_player_id", "reception_player"),
    ("target_player_id", "target_player"),
    ("sack_player_id", "sack_player"),
    ("interception_player_id", "interception_player"),
    ("pass_breakup_player_id", "pass_breakup_player"),
    ("fumble_forced_player_id", "fumble_forced_player"),
]


def _count(frame: pd.DataFrame, id_col: str, name: str) -> pd.Series:
    return frame[id_col].dropna().astype("int64").value_counts().rename(name)


def _sum(frame: pd.DataFrame, id_col: str, val_col: str, name: str) -> pd.Series:
    rows = frame[frame[id_col].notna()]
    return rows.groupby(rows[id_col].astype("int64"))[val_col].sum().rename(name)


def aggregate_season(plays: pd.DataFrame) -> pd.DataFrame:
    """One row per athlete for a single season of play-level rows.

    The feed's ``team`` column is not reliably the offense (it flips on turnovers and
    some defensive plays), so a player's team is inferred as the school present in
    the most of their plays across ``team`` and ``opponent``. On completed-pass
    touchdowns ``touchdown_player`` is sometimes the passer, so any touchdown on a
    completion counts as a passing TD for the passer and a receiving TD for the catcher.
    """
    season = int(plays["season"].iloc[0])
    p = plays
    is_td = p["touchdown_player_id"].notna()
    completed_td = p[is_td & p["completion_player_id"].notna()]
    rush_td = p[is_td & (p["touchdown_player_id"] == p["rush_player_id"])]

    stats = pd.concat(
        [
            _count(p, "completion_player_id", "pass_cmp"),
            _count(p, "incompletion_player_id", "pass_inc"),
            _count(p, "interception_thrown_player_id", "pass_int"),
            _sum(p, "completion_player_id", "completion_yds", "pass_yds"),
            _count(completed_td, "completion_player_id", "pass_td"),
            _count(p, "sack_taken_player_id", "sacks_taken"),
            _count(p, "rush_player_id", "rush_att"),
            _sum(p, "rush_player_id", "rush_yds", "rush_yds"),
            _count(rush_td, "rush_player_id", "rush_td"),
            _count(p, "reception_player_id", "rec"),
            _count(p, "target_player_id", "incomplete_targets"),
            _sum(p, "reception_player_id", "reception_yds", "rec_yds"),
            _count(completed_td, "reception_player_id", "rec_td"),
            _count(p, "sack_player_id", "def_sacks"),
            _count(p, "interception_player_id", "def_int"),
            _count(p, "pass_breakup_player_id", "def_pbu"),
            _count(p, "fumble_forced_player_id", "def_ff"),
        ],
        axis=1,
    ).fillna(0)
    stats.index.name = "athlete_id"

    appearances = pd.concat(
        [
            p.loc[p[id_col].notna(), [id_col, "game_id", "team", "opponent"]].set_axis(
                ["athlete_id", "game_id", "team", "opponent"], axis=1
            )
            for id_col, _ in _ID_NAME_COLUMNS
        ],
        ignore_index=True,
    )
    appearances["athlete_id"] = appearances["athlete_id"].astype("int64")
    stats["games"] = (
        appearances.drop_duplicates(["athlete_id", "game_id"]).groupby("athlete_id").size()
    )
    schools = pd.concat(
        [
            appearances[["athlete_id", "game_id", "team"]],
            appearances[["athlete_id", "game_id", "opponent"]].rename(columns={"opponent": "team"}),
        ]
    ).drop_duplicates()
    stats["team"] = schools.groupby("athlete_id")["team"].agg(lambda s: s.mode().iloc[0])

    names = pd.concat(
        [
            p.loc[p[i].notna(), [i, n]].set_axis(["athlete_id", "player_name"], axis=1)
            for i, n in _ID_NAME_COLUMNS
            if n is not None
        ],
        ignore_index=True,
    )
    names["athlete_id"] = names["athlete_id"].astype("int64")
    stats["player_name"] = names.groupby("athlete_id")["player_name"].agg(
        lambda s: s.mode().iloc[0]
    )
    stats = stats.reset_index()

    # Team totals over the covered games, for market-share features.
    team_games = (
        pd.concat(
            [
                p[["team", "game_id"]],
                p[["opponent", "game_id"]].rename(columns={"opponent": "team"}),
            ]
        )
        .drop_duplicates()
        .groupby("team")
        .size()
        .rename("team_games")
    )
    team_tot = (
        stats.groupby("team")[
            [
                "pass_yds",
                "rush_att",
                "rush_yds",
                "rec",
                "rec_yds",
                "rec_td",
                "rush_td",
                "def_sacks",
                "def_int",
                "def_pbu",
            ]
        ]
        .sum()
        .add_prefix("team_")
    )
    stats = stats.join(team_tot, on="team").join(team_games, on="team")

    conf = (
        p[["team", "conference"]]
        .dropna()
        .groupby("team")["conference"]
        .agg(lambda s: s.mode().iloc[0])
    )
    stats["conference"] = stats["team"].map(conf)
    stats["season"] = season
    stats["name_norm"] = stats["player_name"].map(normalize_name)
    return stats


def add_rates(df: pd.DataFrame) -> pd.DataFrame:
    """Per-game, per-attempt and team-share rates on player-season (or career) rows."""
    out = df.copy()
    g = out["games"].replace(0, np.nan)
    att = out["pass_cmp"] + out["pass_inc"] + out["pass_int"]
    out["pass_att"] = att
    att = att.replace(0, np.nan)
    out["pass_cmp_pct"] = out["pass_cmp"] / att
    out["pass_ypa"] = out["pass_yds"] / att
    out["pass_td_rate"] = out["pass_td"] / att
    out["pass_int_rate"] = out["pass_int"] / att
    out["pass_ypg"] = out["pass_yds"] / g
    out["rush_ypc"] = out["rush_yds"] / out["rush_att"].replace(0, np.nan)
    out["rush_ypg"] = out["rush_yds"] / g
    out["targets"] = out["rec"] + out["incomplete_targets"]
    out["rec_ypg"] = out["rec_yds"] / g
    out["rec_per_game"] = out["rec"] / g
    out["rec_ypr"] = out["rec_yds"] / out["rec"].replace(0, np.nan)
    out["yds_per_target"] = out["rec_yds"] / out["targets"].replace(0, np.nan)
    out["scrimmage_ypg"] = (out["rush_yds"] + out["rec_yds"]) / g
    out["total_td_per_game"] = (out["rush_td"] + out["rec_td"]) / g
    tg = out["team_games"].replace(0, np.nan)
    out["def_sacks_pg"] = out["def_sacks"] / tg
    out["def_int_pg"] = out["def_int"] / tg
    out["def_pbu_pg"] = out["def_pbu"] / tg
    out["def_ff_pg"] = out["def_ff"] / tg
    out["def_ball_production_pg"] = (out["def_int"] + out["def_pbu"]) / tg

    def share(num: str, den: str) -> pd.Series:
        return out[num] / out[den].replace(0, np.nan)

    out["rec_yds_share"] = share("rec_yds", "team_rec_yds")
    out["rec_td_share"] = share("rec_td", "team_rec_td")
    out["dominator"] = out[["rec_yds_share", "rec_td_share"]].mean(axis=1)
    out["rush_att_share"] = share("rush_att", "team_rush_att")
    out["rush_yds_share"] = share("rush_yds", "team_rush_yds")
    out["def_sack_share"] = share("def_sacks", "team_def_sacks")
    return out


def build_player_seasons(season_frames: list[pd.DataFrame]) -> pd.DataFrame:
    return add_rates(pd.concat([aggregate_season(f) for f in season_frames], ignore_index=True))


_SUMMABLE = [
    "pass_cmp",
    "pass_inc",
    "pass_int",
    "pass_yds",
    "pass_td",
    "sacks_taken",
    "rush_att",
    "rush_yds",
    "rush_td",
    "rec",
    "incomplete_targets",
    "rec_yds",
    "rec_td",
    "def_sacks",
    "def_int",
    "def_pbu",
    "def_ff",
    "games",
    "team_pass_yds",
    "team_rush_att",
    "team_rush_yds",
    "team_rec",
    "team_rec_yds",
    "team_rec_td",
    "team_rush_td",
    "team_def_sacks",
    "team_def_int",
    "team_def_pbu",
    "team_games",
]

# Features pulled from the final college season and from the career window.
FINAL_SEASON_FEATURES = [
    "games",
    "pass_att",
    "pass_cmp_pct",
    "pass_ypa",
    "pass_td_rate",
    "pass_int_rate",
    "pass_ypg",
    "rush_att",
    "rush_ypc",
    "rush_ypg",
    "rec_ypg",
    "rec_per_game",
    "rec_ypr",
    "yds_per_target",
    "scrimmage_ypg",
    "total_td_per_game",
    "def_sacks_pg",
    "def_int_pg",
    "def_pbu_pg",
    "def_ff_pg",
    "def_ball_production_pg",
    "rec_yds_share",
    "rec_td_share",
    "dominator",
    "rush_att_share",
    "rush_yds_share",
    "def_sack_share",
]
CAREER_FEATURES = [
    "pass_ypa",
    "pass_td_rate",
    "pass_int_rate",
    "rush_ypc",
    "rec_ypg",
    "yds_per_target",
    "scrimmage_ypg",
    "def_sacks_pg",
    "def_ball_production_pg",
    "rec_yds_share",
    "dominator",
    "rush_yds_share",
]


def summarize_prospect(player_seasons: pd.DataFrame, draft_year: int) -> dict[str, float]:
    """Production features for one prospect from their FBS seasons before ``draft_year``."""
    seasons = player_seasons[player_seasons["season"] < draft_year].sort_values("season")
    if seasons.empty:
        return {}
    final = seasons.iloc[-1]
    out: dict[str, float] = {f"final_{c}": float(final[c]) for c in FINAL_SEASON_FEATURES}
    out["final_season_gap"] = float(draft_year - 1 - final["season"])
    out["college_seasons"] = float(seasons["season"].nunique())

    career = add_rates(seasons[_SUMMABLE].sum().to_frame().T)
    for c in CAREER_FEATURES:
        out[f"career_{c}"] = float(career[c].iloc[0])
    out["best_rec_yds_share"] = float(seasons["rec_yds_share"].max())
    out["best_dominator"] = float(seasons["dominator"].max())
    out["best_def_sacks_pg"] = float(seasons["def_sacks_pg"].max())
    # First season (counting from the earliest covered one) at >= 20% receiving-yard share.
    breakout = seasons.reset_index(drop=True)
    hits = breakout.index[breakout["rec_yds_share"] >= 0.20]
    out["breakout_season_index"] = float(hits[0] + 1) if len(hits) else np.nan
    out["breakout_season"] = float(breakout.loc[hits[0], "season"]) if len(hits) else np.nan
    return out
