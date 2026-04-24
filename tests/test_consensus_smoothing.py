from app.analytics.consensus import DEFAULT_SMOOTHING_ALPHA, _dirichlet_smoothed, _equivalent_candidate_pool_size


def test_equivalent_pool_grows_with_pick() -> None:
    assert _equivalent_candidate_pool_size(1) < _equivalent_candidate_pool_size(32)


def test_dirichlet_smoothing_single_player_not_certain() -> None:
    smooth, p_other, k = _dirichlet_smoothed({"alice": 10.0}, alpha=DEFAULT_SMOOTHING_ALPHA)
    assert k == 2
    assert smooth["alice"] < 1.0
    assert p_other > 0.0
    assert abs(sum(smooth.values()) + p_other - 1.0) < 1e-9


def test_dirichlet_inflated_pool_spreads_mass() -> None:
    smooth, p_other, k = _dirichlet_smoothed(
        {"alice": 1.0}, alpha=DEFAULT_SMOOTHING_ALPHA, equivalent_pool_k=12
    )
    assert k == 12
    assert smooth["alice"] < 0.5
    assert p_other > 0.4
    assert abs(sum(smooth.values()) + p_other - 1.0) < 1e-9


def test_dirichlet_smoothing_two_players_symmetric() -> None:
    smooth, p_other, k = _dirichlet_smoothed({"a": 5.0, "b": 5.0}, alpha=DEFAULT_SMOOTHING_ALPHA)
    assert k == 3
    assert abs(smooth["a"] - smooth["b"]) < 1e-9
    assert smooth["a"] < 0.5
    assert p_other > 0.0
