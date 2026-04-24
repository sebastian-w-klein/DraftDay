from backend.app.org_intelligence.evaluation.backtests import (
    blend_consensus_ml_org,
    org_backtest_summary,
    ranked_labels,
)


def test_org_backtest_summary_includes_ensemble() -> None:
    truths = ["OT", "QB", "CB"]
    base = [{"OT": 0.4, "QB": 0.3, "CB": 0.3}, {"QB": 0.55, "OT": 0.25, "CB": 0.2}, {"CB": 0.5, "OT": 0.3, "QB": 0.2}]
    org = [{"OT": 0.5, "QB": 0.25, "CB": 0.25}, {"QB": 0.6, "OT": 0.2, "CB": 0.2}, {"CB": 0.55, "OT": 0.25, "QB": 0.2}]
    consensus = [{"OT": 0.35, "QB": 0.35, "CB": 0.3}, {"QB": 0.5, "OT": 0.25, "CB": 0.25}, {"CB": 0.45, "OT": 0.3, "QB": 0.25}]
    ensemble = blend_consensus_ml_org(consensus, org)
    summary = org_backtest_summary(
        base_prob_vectors=base,
        org_prob_vectors=org,
        ensemble_prob_vectors=ensemble,
        base_ranked=ranked_labels(base),
        org_ranked=ranked_labels(org),
        ensemble_ranked=ranked_labels(ensemble),
        truths=truths,
    )
    assert "base_ml" in summary
    assert "org_adjusted_ml" in summary
    assert "consensus_ml_org_ensemble" in summary
    assert "log_loss" in summary["consensus_ml_org_ensemble"]
