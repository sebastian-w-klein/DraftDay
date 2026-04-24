from collections import defaultdict

from backend.app.ml.data.roster_loader import RosterRow


def build_need_features(roster_rows: list[RosterRow]) -> list[dict[str, float | int | str]]:
    grouped: dict[tuple[int, str], list[RosterRow]] = defaultdict(list)
    for row in roster_rows:
        grouped[(row.team_id, row.position)].append(row)

    result: list[dict[str, float | int | str]] = []
    for (team_id, position), rows in grouped.items():
        depth_count = len(rows)
        returning_snaps = sum(r.snaps for r in rows)
        returning_starts = sum(r.starts for r in rows)
        avg_age = _safe_avg([r.age for r in rows if r.age is not None])
        avg_experience = _safe_avg([r.experience_years for r in rows if r.experience_years is not None])
        starter_continuity = _safe_avg([1.0 if r.starter_flag else 0.0 for r in rows if r.starter_flag is not None])
        injury_burden = _safe_avg([1.0 if r.injury_flag else 0.0 for r in rows if r.injury_flag is not None])
        result.append(
            {
                "team_id": team_id,
                "position": position,
                "returning_snaps": float(returning_snaps),
                "returning_starts": float(returning_starts),
                "avg_age": avg_age,
                "avg_experience": avg_experience,
                "depth_count": float(depth_count),
                "starter_continuity": starter_continuity,
                "injury_burden": injury_burden,
            }
        )
    return result


def _safe_avg(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))
