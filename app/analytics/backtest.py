from collections import defaultdict

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.entities import ActualDraftPick, DraftCycle, MockPick, Source, SourceAccuracy


def run_source_backtest(db: Session, draft_year: int) -> list[SourceAccuracy]:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == draft_year))
    if cycle is None:
        raise ValueError(f"Unknown draft year: {draft_year}")

    actual_rows = db.scalars(
        select(ActualDraftPick).where(ActualDraftPick.draft_cycle_id == cycle.id)
    ).all()
    if not actual_rows:
        return []

    actual_by_pick = {row.overall_pick: row for row in actual_rows}
    actual_by_player = {row.normalized_player_name: row for row in actual_rows}

    db.execute(delete(SourceAccuracy).where(SourceAccuracy.draft_cycle_id == cycle.id))

    source_rows = db.scalars(select(Source).where(Source.active.is_(True))).all()
    saved: list[SourceAccuracy] = []

    for source in source_rows:
        mock_rows = db.scalars(
            select(MockPick).where(
                MockPick.draft_cycle_id == cycle.id,
                MockPick.source_id == source.id,
            )
        ).all()
        if not mock_rows:
            continue

        exact_hits = 0
        player_team_hits = 0
        round1_hits = 0
        pick_distances: list[int] = []
        player_best_distance: dict[str, int] = defaultdict(lambda: 1000)

        for mock in mock_rows:
            actual_at_pick = actual_by_pick.get(mock.overall_pick)
            if actual_at_pick and actual_at_pick.normalized_player_name == mock.normalized_player_name:
                exact_hits += 1

            actual_for_player = actual_by_player.get(mock.normalized_player_name)
            if actual_for_player is not None:
                if mock.overall_pick <= 32:
                    round1_hits += 1
                distance = abs(mock.overall_pick - actual_for_player.overall_pick)
                pick_distances.append(distance)
                player_best_distance[mock.normalized_player_name] = min(
                    player_best_distance[mock.normalized_player_name], distance
                )
                predicted_team = mock.current_team_id or mock.original_team_id
                if predicted_team is not None and predicted_team == actual_for_player.team_id:
                    player_team_hits += 1

        avg_distance = sum(pick_distances) / len(pick_distances) if pick_distances else 32.0
        weighted = (
            (exact_hits * 4.0) + (player_team_hits * 2.0) + (round1_hits * 1.0) - (avg_distance * 0.25)
        ) / max(1.0, len(mock_rows) / 32.0)

        metric = SourceAccuracy(
            source_id=source.id,
            author_id=None,
            draft_cycle_id=cycle.id,
            exact_pick_hits=exact_hits,
            player_team_hits=player_team_hits,
            round1_player_hits=round1_hits,
            avg_pick_distance=avg_distance,
            weighted_accuracy_score=max(0.0, weighted),
        )
        db.add(metric)
        saved.append(metric)

    db.commit()
    for row in saved:
        db.refresh(row)
    return saved
