from app.ingestion.nflverse_team_aliases import nflverse_team_to_current


def test_houston_oilers_map_to_titans() -> None:
    assert nflverse_team_to_current("HOU", 1995) == "TEN"
    assert nflverse_team_to_current("HOU", 2002) == "HOU"


def test_la_rams_map() -> None:
    assert nflverse_team_to_current("LA", 2016) == "LAR"


def test_static_relocations() -> None:
    assert nflverse_team_to_current("STL", 1999) == "LAR"
    assert nflverse_team_to_current("SD", 2015) == "LAC"
    assert nflverse_team_to_current("OAK", 2019) == "LV"
    assert nflverse_team_to_current("BAL1", 1980) == "IND"
