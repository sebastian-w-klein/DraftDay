from dataclasses import dataclass


@dataclass
class NeedScore:
    team_id: int
    position: str
    short_term_need_score: float
    long_term_need_score: float
    overall_need_score: float
    feature_summary: dict[str, float]


class HeuristicNeedModel:
    """Phase 1 baseline that can later be calibrated by ML."""

    version = "need-heuristic-v1"

    def score(self, rows: list[dict[str, float | int | str]]) -> list[NeedScore]:
        output: list[NeedScore] = []
        for row in rows:
            snaps = float(row.get("returning_snaps", 0.0))
            starts = float(row.get("returning_starts", 0.0))
            depth_count = float(row.get("depth_count", 0.0))
            avg_age = float(row.get("avg_age", 0.0))
            avg_experience = float(row.get("avg_experience", 0.0))
            starter_continuity = float(row.get("starter_continuity", 0.0))
            injury_burden = float(row.get("injury_burden", 0.0))

            snaps_risk = 1.0 - min(1.0, snaps / 3500.0)
            starts_risk = 1.0 - min(1.0, starts / 85.0)
            depth_risk = 1.0 - min(1.0, depth_count / 6.0)
            age_risk = min(1.0, max(0.0, (avg_age - 25.0) / 8.0))
            exp_risk = 1.0 - min(1.0, avg_experience / 6.0)
            continuity_risk = 1.0 - starter_continuity

            short_term = _clip(
                (0.32 * snaps_risk)
                + (0.24 * starts_risk)
                + (0.18 * continuity_risk)
                + (0.12 * injury_burden)
                + (0.14 * depth_risk)
            )
            long_term = _clip((0.4 * age_risk) + (0.35 * exp_risk) + (0.25 * depth_risk))
            overall = _clip((0.55 * short_term) + (0.45 * long_term))

            output.append(
                NeedScore(
                    team_id=int(row["team_id"]),
                    position=str(row["position"]),
                    short_term_need_score=short_term,
                    long_term_need_score=long_term,
                    overall_need_score=overall,
                    feature_summary={
                        "snaps_risk": snaps_risk,
                        "starts_risk": starts_risk,
                        "depth_risk": depth_risk,
                        "age_risk": age_risk,
                        "experience_risk": exp_risk,
                        "continuity_risk": continuity_risk,
                        "injury_burden": injury_burden,
                    },
                )
            )
        return output


def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))
