"""Build the prospect-level analysis table: one row per combine invitee, 2000+.

Population: NFL Scouting Combine invitees (drafted and undrafted). Every drafted
player in the table is now (or was) in the league, which is where the rich
history comes from; undrafted invitees are kept so the analysis also learns what
separates "drafted" from "not drafted".
"""

from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd

from backend.app.draft_slot import college_production, config, features, sources
from backend.app.draft_slot.college_production import normalize_name

# Combine school spellings that do not normalize onto an ESPN/CFBD school name.
SCHOOL_ALIASES = {
    "mississippi": "ole miss",
    "boston col": "boston college",
    "north carolina state": "nc state",
    "ala birmingham": "uab",
    "tenn chattanooga": "chattanooga",
    "tennessee chattanooga": "chattanooga",
    "louisiana lafayette": "louisiana",
    "louisiana st": "lsu",
    "nw state la": "northwestern state",
    "northwestern state la": "northwestern state",
    "ark pine bluff": "arkansas pine bluff",
    "university of arkansas at pine bluff": "arkansas pine bluff",
    "citadel": "the citadel",
    "middle tenn state": "middle tennessee",
    "miami ohio": "miami oh",
    "southern utah state": "southern utah",
    "houston christian university": "houston christian",
    "central missouri state": "central missouri",
    "fayetteville state university": "fayetteville state",
    "duluth university of minnesota": "minnesota duluth",
    "kutztown pennsylvania": "kutztown",
    "malone university ohio": "malone",
    "northeastern ma": "northeastern",
}


def normalize_school(name: object) -> str:
    if not isinstance(name, str):
        return ""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    value = normalize_name(ascii_name.replace("&", " and "))
    words = value.split()
    replacements = {"st": "state", "west": "western", "east": "eastern", "col": "college"}
    # "St." is "State" at the end of a name (Ohio St.) but "Saint" at the start (St. Cloud).
    words = [
        replacements.get(w, w) if not (w == "st" and i == 0) else "saint"
        for i, w in enumerate(words)
    ]
    value = " ".join(words)
    value = SCHOOL_ALIASES.get(value, value)
    # Aliases may themselves need the abbreviation expansion (e.g. "middle tenn state").
    return SCHOOL_ALIASES.get(value, value)


def _parse_height(value: object) -> float:
    if not isinstance(value, str) or "-" not in value:
        return np.nan
    feet, inches = value.split("-", 1)
    try:
        return int(feet) * 12 + float(inches)
    except ValueError:
        return np.nan


def _school_lookup(team_info: pd.DataFrame) -> pd.DataFrame:
    """Normalized alias -> (school, season, conference, classification)."""
    rows = []
    for col in ["school", "abbreviation", "alt_name1", "alt_name2", "alt_name3"]:
        part = team_info[team_info[col].notna()]
        part = part.assign(school_key=part[col].map(normalize_school))
        rows.append(part[["school_key", "school", "season", "conference", "classification"]])
    lookup = pd.concat(rows, ignore_index=True)
    lookup = lookup[lookup["school_key"] != ""]
    # Prefer the canonical-name match when an alias collides across schools.
    lookup["is_canonical"] = lookup["school_key"] == lookup["school"].map(normalize_school)
    lookup = lookup.sort_values("is_canonical", ascending=False).drop_duplicates(
        ["school_key", "season"]
    )
    return lookup.drop(columns="is_canonical")


def _attach_school_context(df: pd.DataFrame, team_info: pd.DataFrame) -> pd.DataFrame:
    lookup = _school_lookup(team_info)
    df = df.copy()
    df["school_key"] = df["school"].map(normalize_school)
    df["context_season"] = df["draft_year"] - 1

    # Exact season when available, otherwise the nearest covered season for that school.
    exact = df.merge(
        lookup,
        left_on=["school_key", "context_season"],
        right_on=["school_key", "season"],
        how="left",
        suffixes=("", "_ti"),
    ).drop(columns=["season_ti"], errors="ignore")
    missing = exact["school_ti"].isna() if "school_ti" in exact else exact["conference"].isna()
    exact = exact.rename(columns={"school_ti": "cfb_school"})
    if missing.any():
        nearest = []
        by_key = {k: g for k, g in lookup.groupby("school_key")}
        for idx in exact.index[missing]:
            group = by_key.get(exact.at[idx, "school_key"])
            if group is None:
                nearest.append((idx, None, None, None))
                continue
            row = group.iloc[(group["season"] - exact.at[idx, "context_season"]).abs().argmin()]
            nearest.append((idx, row["school"], row["conference"], row["classification"]))
        for idx, school, conference, classification in nearest:
            exact.at[idx, "cfb_school"] = school
            exact.at[idx, "conference"] = conference
            exact.at[idx, "classification"] = classification
    return exact


def _power_flag(conference: object, school: object, season: int) -> float:
    if not isinstance(conference, str):
        return 0.0
    if school == "Notre Dame":
        return 1.0
    for start, end, conferences in config.POWER_CONFERENCES_BY_ERA:
        if start <= season <= end:
            return float(conference in conferences)
    return 0.0


def _link_production(df: pd.DataFrame, player_seasons: pd.DataFrame) -> pd.DataFrame:
    """Attach college production for draft classes covered by the play-level feed.

    Link order: (1) ESPN athlete id via the nflverse players table, (2) normalized
    name + school in any season of the four before the draft, (3) normalized name
    alone when it is unique among final-season candidates.
    """
    ps = player_seasons.copy()
    ps["school_key"] = ps["team"].map(normalize_school)
    by_id = {k: g for k, g in ps.groupby("athlete_id")}
    name_school = ps.groupby(["name_norm", "school_key"])["athlete_id"].agg(set)
    name_season = ps.groupby(["name_norm", "season"])["athlete_id"].agg(set)

    records = []
    for idx, row in df.iterrows():
        year = int(row["draft_year"])
        if year - 1 < config.FIRST_CFB_STATS_SEASON:
            continue
        athlete_id, method = None, None
        espn = row.get("espn_id")
        if pd.notna(espn) and int(espn) in by_id:
            athlete_id, method = int(espn), "espn_id"
        if athlete_id is None:
            ids = name_school.get((row["name_norm"], row["cfb_school_key"]), set())
            ids = {i for i in ids if (by_id[i]["season"].between(year - 5, year - 1)).any()}
            if len(ids) == 1:
                athlete_id, method = next(iter(ids)), "name_school"
        if athlete_id is None:
            ids = name_season.get((row["name_norm"], year - 1), set())
            if len(ids) == 1:
                athlete_id, method = next(iter(ids)), "name_unique"
        if athlete_id is None:
            continue
        seasons = by_id[athlete_id]
        summary = college_production.summarize_prospect(seasons, year)
        if not summary:
            continue
        summary.update({"row_idx": idx, "cfb_athlete_id": athlete_id, "production_link": method})
        records.append(summary)
    if not records:
        return df
    prod = pd.DataFrame.from_records(records).set_index("row_idx")
    return df.join(prod)


def build_dataset(refresh: bool = False, with_production: bool = True) -> pd.DataFrame:
    combine = sources.load_combine(refresh)
    picks = sources.load_draft_picks(refresh)
    players = sources.load_players(refresh)
    team_info = sources.load_cfb_team_info(range(config.FIRST_COMBINE_YEAR, 2027), refresh)

    # combine.draft_year is only filled for drafted players; the combine season is the
    # draft year for everyone.
    df = combine.assign(draft_year=combine["season"])
    df = df[df["draft_year"] >= config.FIRST_COMBINE_YEAR].copy()
    df = df[~df["pos"].isin(config.EXCLUDED_POSITIONS)]
    df["height_in"] = df["ht"].map(_parse_height)
    df = df.rename(columns={"wt": "weight_lb", "broad_jump": "broad"})

    # Draft outcome. combine.draft_ovr is authoritative; fill any gaps from draft_picks.
    pk = picks.dropna(subset=["pfr_player_id"])[
        ["pfr_player_id", "season", "pick", "round", "age"]
    ].rename(columns={"pfr_player_id": "pfr_id", "season": "draft_year", "age": "pfr_age"})
    df = df.merge(pk, on=["pfr_id", "draft_year"], how="left")
    df["overall_pick"] = df["draft_ovr"].fillna(df["pick"])
    df["drafted"] = df["overall_pick"].notna().astype(int)
    df["draft_round"] = df["draft_round"].fillna(df["round"])
    df = df.drop(columns=["pick", "round", "draft_ovr"])

    pl = players.dropna(subset=["pfr_id"]).drop_duplicates("pfr_id")[
        ["pfr_id", "birth_date", "espn_id"]
    ]
    df = df.merge(pl, on="pfr_id", how="left")
    draft_day = pd.to_datetime(df["draft_year"].astype(str) + "-04-25")
    df["birth_dt"] = pd.to_datetime(df["birth_date"], errors="coerce")
    df["age_at_draft"] = (draft_day - df["birth_dt"]).dt.days / 365.25
    # PFR age is an integer age in the draft season; use it when there is no birth
    # date, or when the birth date disagrees with it (pfr_id collisions in the
    # players table produce a few impossible ages).
    pfr_age = df["pfr_age"] + 0.5
    disagrees = (df["age_at_draft"] - pfr_age).abs() > 1.5
    df.loc[disagrees, "age_at_draft"] = pfr_age[disagrees]
    df["age_at_draft"] = df["age_at_draft"].fillna(pfr_age)
    implausible = ~df["age_at_draft"].between(19.0, 30.0)
    df.loc[implausible, "age_at_draft"] = np.nan
    df.loc[disagrees | implausible, "birth_dt"] = pd.NaT

    df = _attach_school_context(df, team_info)
    df["power_conf"] = [
        _power_flag(c, s, y)
        for c, s, y in zip(df["conference"], df["cfb_school"], df["context_season"], strict=True)
    ]
    df["fbs"] = (df["classification"] == "fbs").astype(float)
    df["cfb_school_key"] = (
        df["cfb_school"].map(normalize_school).where(df["cfb_school"].notna(), df["school_key"])
    )
    df["name_norm"] = df["player_name"].map(normalize_name)

    if with_production:
        seasons = [
            sources.load_cfb_play_stats(s, refresh)
            for s in range(config.FIRST_CFB_STATS_SEASON, int(df["draft_year"].max()))
        ]
        player_seasons = college_production.build_player_seasons(
            [f for f in seasons if f is not None]
        )
        df = _link_production(df, player_seasons)
        if "breakout_season" in df:
            breakout_date = pd.to_datetime(
                df["breakout_season"].dropna().astype(int).astype(str) + "-09-01"
            ).reindex(df.index)
            df["breakout_age"] = (breakout_date - df["birth_dt"]).dt.days / 365.25

    df = features.add_features(df)
    return df.reset_index(drop=True)
