from backend.app.ml.models.position_model import PositionModel


def test_position_model_train_and_predict() -> None:
    model = PositionModel()
    rows = [
        {
            "need_score": 0.9,
            "board_scarcity_score": 0.6,
            "best_available_player_score": 0.8,
            "overall_pick": 5,
            "round_number": 1,
            "top_need_position": "OT",
            "label_position": "OT",
        },
        {
            "need_score": 0.7,
            "board_scarcity_score": 0.5,
            "best_available_player_score": 0.4,
            "overall_pick": 10,
            "round_number": 1,
            "top_need_position": "CB",
            "label_position": "CB",
        },
        {
            "need_score": 0.4,
            "board_scarcity_score": 0.2,
            "best_available_player_score": 0.9,
            "overall_pick": 2,
            "round_number": 1,
            "top_need_position": "EDGE",
            "label_position": "EDGE",
        },
    ]
    bundle = model.train(rows)
    probs = model.predict_proba(
        bundle,
        {
            "need_score": 0.8,
            "board_scarcity_score": 0.5,
            "best_available_player_score": 0.7,
            "overall_pick": 6,
            "round_number": 1,
            "top_need_position": "OT",
        },
    )
    assert probs
    assert abs(sum(probs.values()) - 1.0) < 1e-6
