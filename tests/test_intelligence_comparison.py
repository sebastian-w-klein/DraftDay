from backend.app.ml.inference.predictor import (
    compute_disagreement_score,
    compute_superstar_override_score,
)


def test_compute_disagreement_score() -> None:
    score = compute_disagreement_score(
        ["cam ward", "travis hunter", "will campbell"],
        ["travis hunter", "mason graham", "will campbell"],
    )
    assert 0.0 <= score <= 1.0
    assert score > 0.0


def test_superstar_override_score_higher_when_need_is_lower() -> None:
    low_need_high_talent = compute_superstar_override_score(0.2, 0.95, 0.7)
    high_need_high_talent = compute_superstar_override_score(0.9, 0.95, 0.7)
    assert 0.0 <= low_need_high_talent <= 1.0
    assert low_need_high_talent > high_need_high_talent
