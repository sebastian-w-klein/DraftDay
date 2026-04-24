from backend.app.ml.data.board_context_loader import BoardContextRow


def build_context_features(rows: list[BoardContextRow]) -> list[dict[str, float | int | str | None]]:
    return [
        {
            "team_id": row.team_id,
            "overall_pick": row.overall_pick,
            "round_number": row.round_number,
            "board_scarcity_score": row.board_scarcity_score,
            "best_available_player_score": row.best_available_player_score,
            "top_need_position": row.top_need_position,
        }
        for row in rows
    ]
