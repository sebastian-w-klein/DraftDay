from backend.app.ml.evaluation.metrics import multiclass_log_loss, top_k_hit_rate


def evaluate_org_adjusted_positions(
    prob_vectors: list[dict[str, float]], ranked_positions: list[list[str]], truths: list[str]
) -> dict[str, float]:
    return {
        "log_loss": multiclass_log_loss(prob_vectors, truths),
        "top1_accuracy": top_k_hit_rate(ranked_positions, truths, 1),
        "top3_accuracy": top_k_hit_rate(ranked_positions, truths, 3),
    }
