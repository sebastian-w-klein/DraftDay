from backend.app.ml.models.need_model import HeuristicNeedModel


def test_heuristic_need_model_scores_in_range() -> None:
    model = HeuristicNeedModel()
    rows = [
        {
            "team_id": 1,
            "position": "QB",
            "returning_snaps": 1200.0,
            "returning_starts": 18.0,
            "avg_age": 28.5,
            "avg_experience": 2.0,
            "depth_count": 2.0,
            "starter_continuity": 0.2,
            "injury_burden": 0.4,
        }
    ]
    scores = model.score(rows)
    assert len(scores) == 1
    assert 0 <= scores[0].short_term_need_score <= 1
    assert 0 <= scores[0].long_term_need_score <= 1
    assert 0 <= scores[0].overall_need_score <= 1
