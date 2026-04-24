"""Map nfldata / nflverse `draft_picks.team` codes to current `teams.abbreviation` values."""


def nflverse_team_to_current(abbrev: str, season: int) -> str:
    """Map historical nfldata `team` codes to current NFL abbreviations in our `teams` table."""
    u = abbrev.strip().upper()
    if u == "HOU" and season < 2002:
        return "TEN"
    if u == "LA":
        return "LAR"
    static = {
        "STL": "LAR",
        "SD": "LAC",
        "OAK": "LV",
        "LARD": "LV",
        "LARM": "LAR",
        "PHO": "ARI",
        "BAL1": "IND",
    }
    return static.get(u, u)
