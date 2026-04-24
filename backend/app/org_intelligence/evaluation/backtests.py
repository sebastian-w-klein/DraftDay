from backend.app.org_intelligence.evaluation.metrics import evaluate_org_adjusted_positions


def org_backtest_summary(
    base_prob_vectors: list[dict[str, float]],
    org_prob_vectors: list[dict[str, float]],
    ensemble_prob_vectors: list[dict[str, float]],
    base_ranked: list[list[str]],
    org_ranked: list[list[str]],
    ensemble_ranked: list[list[str]],
    truths: list[str],
) -> dict[str, dict[str, float]]:
    return {
        "base_ml": evaluate_org_adjusted_positions(base_prob_vectors, base_ranked, truths),
        "org_adjusted_ml": evaluate_org_adjusted_positions(org_prob_vectors, org_ranked, truths),
        "consensus_ml_org_ensemble": evaluate_org_adjusted_positions(
            ensemble_prob_vectors, ensemble_ranked, truths
        ),
    }


def blend_consensus_ml_org(
    consensus_prob_vectors: list[dict[str, float]],
    ml_org_prob_vectors: list[dict[str, float]],
    alpha: float = 0.45,
    beta: float = 0.55,
) -> list[dict[str, float]]:
    blended: list[dict[str, float]] = []
    for consensus, ml_org in zip(consensus_prob_vectors, ml_org_prob_vectors):
        keys = set(consensus.keys()).union(set(ml_org.keys()))
        row: dict[str, float] = {}
        for key in keys:
            row[key] = (alpha * consensus.get(key, 0.0)) + (beta * ml_org.get(key, 0.0))
        total = sum(row.values()) or 1.0
        blended.append({k: v / total for k, v in row.items()})
    return blended


def ranked_labels(prob_vectors: list[dict[str, float]]) -> list[list[str]]:
    return [list(dict(sorted(row.items(), key=lambda item: item[1], reverse=True)).keys()) for row in prob_vectors]
