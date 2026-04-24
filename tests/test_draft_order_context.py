from app.draft_order_context import next_unfilled_round1_overall_for_team


def test_next_pick_skips_filled_and_uses_order() -> None:
    filled = {1, 2, 3, 4, 5, 6, 7}
    order = [
        (1, "CLE"),
        (2, "NYG"),
        (8, "TEN"),
        (9, "CHI"),
    ]
    assert next_unfilled_round1_overall_for_team(filled, order, "TEN") == 8


def test_next_pick_first_slot_for_team() -> None:
    filled: set[int] = set()
    order = [(1, "BUF"), (2, "MIA")]
    assert next_unfilled_round1_overall_for_team(filled, order, "MIA") == 2


def test_next_pick_none_when_no_slots() -> None:
    filled = {1}
    order = [(1, "BUF")]
    assert next_unfilled_round1_overall_for_team(filled, order, "BUF") is None


def test_next_pick_respects_max_overall() -> None:
    filled: set[int] = set()
    order = [(31, "ARI"), (33, "ARI")]
    assert next_unfilled_round1_overall_for_team(filled, order, "ARI", max_overall=32) == 31
