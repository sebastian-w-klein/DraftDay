from backend.app.ml.features.candidate_features import CandidateInput, build_candidate_features


def test_candidate_feature_generation_has_rank_gaps_and_fit_metrics() -> None:
    rows = build_candidate_features(
        team_need_by_position={"QB": 0.9, "OT": 0.75},
        board_scarcity_score=0.4,
        candidates=[
            CandidateInput(
                player_id=1,
                player_name="Cam Ward",
                position="QB",
                prospect_score=0.88,
                superstar_potential_score=0.81,
                consensus_rank=1,
                best_available_rank=1,
                best_rank_in_position=1,
            ),
            CandidateInput(
                player_id=2,
                player_name="Will Campbell",
                position="OT",
                prospect_score=0.82,
                superstar_potential_score=0.66,
                consensus_rank=5,
                best_available_rank=1,
                best_rank_in_position=1,
            ),
        ],
    )
    assert len(rows) == 2
    assert rows[0]["team_need_score"] == 0.9
    assert rows[1]["rank_gap_from_best_available"] == 4.0
    assert "fit_gap" in rows[1]
    assert "need_vs_bpa_gap" in rows[1]
