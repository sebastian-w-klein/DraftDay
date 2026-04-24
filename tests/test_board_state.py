from app.board_state import board_cache_suffix


def test_board_cache_suffix_empty() -> None:
    assert board_cache_suffix(frozenset()) == ""


def test_board_cache_suffix_order_invariant() -> None:
    a = board_cache_suffix(frozenset(["cam ward", "travis hunter"]))
    b = board_cache_suffix(frozenset(["travis hunter", "cam ward"]))
    assert a == b
    assert a.startswith("b")
