from backend.app.ml.data.prospect_loader import ProspectRow


def build_prospect_features(rows: list[ProspectRow]) -> list[dict[str, float | str | int | None]]:
    output: list[dict[str, float | str | int | None]] = []
    for row in rows:
        consensus_signal = 0.0 if row.consensus_rank is None else max(0.0, 1.0 - (row.consensus_rank / 300.0))
        output.append(
            {
                "player_id": row.player_id,
                "full_name": row.full_name,
                "position": row.position,
                "prospect_score": row.prospect_score,
                "superstar_potential_score": row.superstar_potential_score,
                "consensus_rank": row.consensus_rank,
                "consensus_signal": consensus_signal,
            }
        )
    return output
