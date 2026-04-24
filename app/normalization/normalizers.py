import re
import string
from dataclasses import dataclass


POSITION_MAP: dict[str, str] = {
    "qb": "QB",
    "rb": "RB",
    "wr": "WR",
    "te": "TE",
    "ot": "OT",
    "t": "OT",
    "iol": "IOL",
    "c": "C",
    "g": "G",
    "og": "G",
    "edge": "EDGE",
    "de": "EDGE",
    "dt": "DT",
    "idl": "DT",
    "lb": "LB",
    "cb": "CB",
    "s": "S",
    "fs": "S",
    "ss": "S",
    "k": "K",
    "p": "P",
}


def normalize_text(value: str) -> str:
    compact = value.strip().lower()
    compact = compact.translate(str.maketrans("", "", string.punctuation))
    compact = re.sub(r"\s+", " ", compact)
    compact = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", compact).strip()
    return compact


_NFL_TEAM_ROWS: list[tuple[str, str, str]] = [
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


def _freeze_team_aliases() -> dict[str, str]:
    """Map normalized free-text team labels to NFL abbreviations."""
    m: dict[str, str] = {}
    multi_city = frozenset({"los angeles", "new york"})
    for abbr, full_name, city in _NFL_TEAM_ROWS:
        m[normalize_text(full_name)] = abbr
        ckey = normalize_text(city)
        if ckey not in multi_city:
            m[ckey] = abbr
    extras: list[tuple[str, str]] = [
        ("los angeles chargers", "LAC"),
        ("la chargers", "LAC"),
        ("los angeles rams", "LAR"),
        ("la rams", "LAR"),
        ("chargers", "LAC"),
        ("rams", "LAR"),
        ("new york giants", "NYG"),
        ("new york jets", "NYJ"),
        ("ny giants", "NYG"),
        ("ny jets", "NYJ"),
        ("giants", "NYG"),
        ("jets", "NYJ"),
        ("washington commanders", "WAS"),
        ("washington football team", "WAS"),
        ("washington", "WAS"),
        ("niners", "SF"),
    ]
    for label, abbr in extras:
        m[normalize_text(label)] = abbr
    for abbr, full_name, _ in _NFL_TEAM_ROWS:
        parts = full_name.split()
        if not parts:
            continue
        nick = normalize_text(parts[-1])
        if nick in m and m[nick] != abbr:
            continue
        m[nick] = abbr
    for label, abbr in extras:
        m[normalize_text(label)] = abbr
    return m


TEAM_ALIASES: dict[str, str] = _freeze_team_aliases()

SCHOOL_ALIASES: dict[str, str] = {
    "ohio st": "ohio state",
    "ole miss": "mississippi",
    "louisiana state": "lsu",
}


@dataclass
class NormalizedPick:
    player_name: str
    position: str | None
    school: str | None
    original_team: str | None
    current_team: str | None


def normalize_position(position: str | None) -> str | None:
    if position is None:
        return None
    key = normalize_text(position)
    return POSITION_MAP.get(key, position.upper())


def normalize_school(school: str | None) -> str | None:
    if school is None:
        return None
    key = normalize_text(school)
    return SCHOOL_ALIASES.get(key, key)


def normalize_team(team: str | None) -> str | None:
    if team is None:
        return None
    t = team.strip()
    if not t:
        return None
    if len(t) <= 4:
        letters = "".join(c for c in t if c.isalpha())
        return letters.upper() if letters else None
    key = normalize_text(t)
    return TEAM_ALIASES.get(key)


def normalize_player_name(name: str) -> str:
    return normalize_text(name)
