from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "data" / "draft_slot" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "draft_slot" / "processed"
ARTIFACT_DIR = REPO_ROOT / "backend" / "artifacts" / "draft_slot"

NFLVERSE_RELEASES = "https://github.com/nflverse/nflverse-data/releases/download"
COMBINE_URL = f"{NFLVERSE_RELEASES}/combine/combine.csv"
DRAFT_PICKS_URL = f"{NFLVERSE_RELEASES}/draft_picks/draft_picks.csv"
PLAYERS_URL = f"{NFLVERSE_RELEASES}/players/players.csv"

CFBFASTR_RAW = "https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/main"
CFB_PLAYER_STATS_URL = CFBFASTR_RAW + "/player_stats/parquet/player_stats_{season}.parquet"
CFB_TEAM_INFO_URL = CFBFASTR_RAW + "/team_info/parquet/cfb_team_info_{season}.parquet"

FIRST_COMBINE_YEAR = 2000
# cfbfastR play-level player stats start with the 2014 season (the 2015 draft class).
FIRST_CFB_STATS_SEASON = 2014

# Assigned to undrafted players wherever a single pick-like number is needed.
# Real drafts end near pick 257-262; 300 sits clearly beyond every drafted player.
UNDRAFTED_PICK = 300

# Combine labels -> analysis position groups. OLB and generic DL/LB labels are
# resolved by weight in ``features.assign_position_group``.
POSITION_GROUP_MAP: dict[str, str] = {
    "QB": "QB",
    "RB": "RB",
    "FB": "RB",
    "WR": "WR",
    "CB/WR": "WR",
    "TE": "TE",
    "OT": "OT",
    "OG": "IOL",
    "G": "IOL",
    "C": "IOL",
    "OL": "IOL",
    "DE": "EDGE",
    "EDGE": "EDGE",
    "DT": "IDL",
    "DL": "IDL",
    "ILB": "LB",
    "LB": "LB",
    "OLB": "LB",
    "CB": "CB",
    "S": "S",
    "SAF": "S",
    "DB": "S",
}
# Specialists are excluded: their draft slot is not driven by the same traits.
EXCLUDED_POSITIONS = {"K", "P", "LS"}
POSITION_GROUPS = ["QB", "RB", "WR", "TE", "OT", "IOL", "EDGE", "IDL", "LB", "CB", "S"]

# Conferences treated as the top tier ("Power") for each season. The Big East
# (football) counts through 2012; the Pac-12 counts through 2023.
POWER_CONFERENCES_BY_ERA: list[tuple[int, int, set[str]]] = [
    (2000, 2012, {"ACC", "Big 12", "Big East", "Big Ten", "Pac-10", "Pac-12", "SEC"}),
    (2013, 2023, {"ACC", "Big 12", "Big Ten", "Pac-12", "SEC"}),
    (2024, 2100, {"ACC", "Big 12", "Big Ten", "SEC"}),
]
