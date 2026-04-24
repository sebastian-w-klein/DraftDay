from backend.app.ml.models.player_model import PlayerModel


def test_player_model_train_predict_probabilities() -> None:
    model = PlayerModel()
    rows = [
        {
            "candidate_player_name": "Player A",
            "position": "QB",
            "team_need_score": 0.9,
            "prospect_score": 0.88,
            "superstar_potential_score": 0.85,
            "positional_scarcity_score": 0.4,
            "consensus_rank": 1,
            "rank_gap_from_best_available": 0.0,
            "rank_gap_within_position": 0.0,
            "fit_gap": 0.02,
            "need_vs_bpa_gap": 0.02,
            "selected_label": True,
        },
        {
            "candidate_player_name": "Player B",
            "position": "OT",
            "team_need_score": 0.5,
            "prospect_score": 0.6,
            "superstar_potential_score": 0.4,
            "positional_scarcity_score": 0.3,
            "consensus_rank": 20,
            "rank_gap_from_best_available": 19.0,
            "rank_gap_within_position": 7.0,
            "fit_gap": 0.1,
            "need_vs_bpa_gap": -0.1,
            "selected_label": False,
        },
        {
            "candidate_player_name": "Player C",
            "position": "CB",
            "team_need_score": 0.7,
            "prospect_score": 0.75,
            "superstar_potential_score": 0.72,
            "positional_scarcity_score": 0.6,
            "consensus_rank": 8,
            "rank_gap_from_best_available": 7.0,
            "rank_gap_within_position": 2.0,
            "fit_gap": 0.05,
            "need_vs_bpa_gap": -0.05,
            "selected_label": True,
        },
        {
            "candidate_player_name": "Player D",
            "position": "RB",
            "team_need_score": 0.2,
            "prospect_score": 0.4,
            "superstar_potential_score": 0.3,
            "positional_scarcity_score": 0.1,
            "consensus_rank": 45,
            "rank_gap_from_best_available": 44.0,
            "rank_gap_within_position": 20.0,
            "fit_gap": 0.2,
            "need_vs_bpa_gap": -0.2,
            "selected_label": False,
        },
    ]
    bundle = model.train(rows)
    probs = model.predict_proba(bundle, rows)
    assert len(probs) == 4
    assert all(0.0 <= prob <= 1.0 for prob in probs)
