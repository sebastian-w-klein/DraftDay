from backend.app.ml.features.roster_strength import adjusted_overall_need, roster_strength_proxy
from backend.app.ml.data.roster_loader import RosterRow


def test_roster_strength_proxy_qb() -> None:
    rows = [RosterRow(team_id=1, position="QB", snaps=1100, starts=17, age=26.0, experience_years=4.0, starter_flag=True, injury_flag=False)]
    assert roster_strength_proxy(1, "QB", rows) > 0.95


def test_adjusted_need_drops_with_strong_room() -> None:
    base = 0.9
    assert adjusted_overall_need(base, 0.0) == base
    assert adjusted_overall_need(base, 1.0) < 0.35
