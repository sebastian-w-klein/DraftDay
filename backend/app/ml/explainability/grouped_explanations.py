def grouped_feature_explanations(summary: dict[str, float | str | int]) -> dict[str, float]:
    need = float(summary.get("need_score", 0.0))
    context = (
        float(summary.get("board_scarcity_score", 0.0))
        + float(summary.get("best_available_player_score", 0.0))
    ) / 2.0
    return {
        "need_component": need,
        "talent_component": float(summary.get("best_available_player_score", 0.0)),
        "context_component": context,
    }
