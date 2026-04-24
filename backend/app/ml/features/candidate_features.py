from dataclasses import dataclass


@dataclass
class CandidateInput:
    player_id: int | None
    player_name: str
    position: str
    prospect_score: float
    superstar_potential_score: float
    consensus_rank: int | None
    best_available_rank: int | None
    best_rank_in_position: int | None
    selected_label: bool = False


def build_candidate_features(
    team_need_by_position: dict[str, float],
    board_scarcity_score: float,
    candidates: list[CandidateInput],
) -> list[dict[str, float | str | int | bool | None]]:
    rows: list[dict[str, float | str | int | bool | None]] = []
    for candidate in candidates:
        need_score = float(team_need_by_position.get(candidate.position, 0.25))
        consensus_rank = candidate.consensus_rank
        best_available_rank = candidate.best_available_rank or consensus_rank or 300
        best_rank_in_position = candidate.best_rank_in_position or consensus_rank or 300
        rank_gap_from_best_available = float((consensus_rank or 300) - best_available_rank)
        rank_gap_within_position = float((consensus_rank or 300) - best_rank_in_position)
        fit_gap = abs(need_score - candidate.prospect_score)
        need_vs_bpa_gap = need_score - candidate.prospect_score
        rows.append(
            {
                "candidate_player_id": candidate.player_id,
                "candidate_player_name": candidate.player_name,
                "position": candidate.position,
                "team_need_score": need_score,
                "prospect_score": candidate.prospect_score,
                "superstar_potential_score": candidate.superstar_potential_score,
                "consensus_rank": consensus_rank,
                "rank_gap_from_best_available": rank_gap_from_best_available,
                "rank_gap_within_position": rank_gap_within_position,
                "positional_scarcity_score": float(board_scarcity_score),
                "fit_gap": fit_gap,
                "need_vs_bpa_gap": need_vs_bpa_gap,
                "available_at_pick": True,
                "selected_label": candidate.selected_label,
            }
        )
    return rows
