from backend.app.org_intelligence.data.coach_loader import CoachProfileRow


def coach_feature_vector(row: CoachProfileRow | None) -> dict[str, float]:
    if row is None:
        return {
            "coach_offense_bias": 0.5,
            "coach_defense_bias": 0.5,
            "coach_trenches_bias": 0.5,
            "coach_skill_bias": 0.5,
        }
    return {
        "coach_offense_bias": row.prior_offense_pick_share,
        "coach_defense_bias": row.prior_defense_pick_share,
        "coach_trenches_bias": row.prior_trenches_pick_share,
        "coach_skill_bias": row.prior_skill_pick_share,
    }
