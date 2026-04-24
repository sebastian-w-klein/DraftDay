from math import log


def top_k_hit_rate(predictions: list[list[str]], truths: list[str], k: int) -> float:
    if not predictions or not truths:
        return 0.0
    hits = 0
    for pred, truth in zip(predictions, truths):
        if truth in pred[:k]:
            hits += 1
    return hits / len(truths)


def multiclass_log_loss(prob_vectors: list[dict[str, float]], truths: list[str]) -> float:
    if not prob_vectors or not truths:
        return 0.0
    total = 0.0
    for probs, truth in zip(prob_vectors, truths):
        p = max(1e-12, min(1.0, probs.get(truth, 1e-12)))
        total += -log(p)
    return total / len(truths)
