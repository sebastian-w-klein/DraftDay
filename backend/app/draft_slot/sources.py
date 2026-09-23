"""Download and cache the public datasets used by the draft-slot research.

Sources (attribute in any public use):
- nflverse combine / draft_picks / players releases (CC BY 4.0 / PFR lineage)
- sportsdataverse cfbfastR-data play-level player stats and team info (ESPN / CFBD lineage)
"""

from __future__ import annotations

import shutil
import urllib.error
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

from backend.app.draft_slot import config


def _download(url: str, dest: Path, refresh: bool = False) -> Path | None:
    if dest.exists() and not refresh:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urlopen(url, timeout=300) as resp, tmp.open("wb") as out:  # noqa: S310
            shutil.copyfileobj(resp, out)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    tmp.replace(dest)
    return dest


def load_combine(refresh: bool = False) -> pd.DataFrame:
    path = _download(config.COMBINE_URL, config.RAW_DIR / "combine.csv", refresh)
    assert path is not None
    return pd.read_csv(path)


def load_draft_picks(refresh: bool = False) -> pd.DataFrame:
    path = _download(config.DRAFT_PICKS_URL, config.RAW_DIR / "draft_picks.csv", refresh)
    assert path is not None
    return pd.read_csv(path, low_memory=False)


def load_players(refresh: bool = False) -> pd.DataFrame:
    path = _download(config.PLAYERS_URL, config.RAW_DIR / "players.csv", refresh)
    assert path is not None
    return pd.read_csv(path, low_memory=False)


def load_cfb_team_info(seasons: range, refresh: bool = False) -> pd.DataFrame:
    frames = []
    for season in seasons:
        path = _download(
            config.CFB_TEAM_INFO_URL.format(season=season),
            config.RAW_DIR / "cfb_team_info" / f"{season}.parquet",
            refresh,
        )
        if path is None:
            continue
        frame = pd.read_parquet(
            path,
            columns=[
                "school",
                "abbreviation",
                "alt_name1",
                "alt_name2",
                "alt_name3",
                "conference",
                "classification",
            ],
        )
        frame["season"] = season
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)


PLAY_STAT_COLUMNS = [
    "game_id",
    "season",
    "team",
    "conference",
    "opponent",
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


def load_cfb_play_stats(season: int, refresh: bool = False) -> pd.DataFrame | None:
    path = _download(
        config.CFB_PLAYER_STATS_URL.format(season=season),
        config.RAW_DIR / "cfb_player_stats" / f"{season}.parquet",
        refresh,
    )
    if path is None:
        return None
    frame = pd.read_parquet(path)
    return frame[[c for c in PLAY_STAT_COLUMNS if c in frame.columns]]
