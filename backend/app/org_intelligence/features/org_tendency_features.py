from app.models.entities import TeamOrgTendencyFeature


def org_tendency_feature_vector(row: TeamOrgTendencyFeature | None) -> dict[str, float]:
    if row is None:
        return {
            "org_offense_share": 0.5,
            "org_defense_share": 0.5,
            "org_trenches_share": 0.5,
            "org_need_follow_rate": 0.5,
            "org_bpa_deviation_rate": 0.5,
            "regime_stability_score": 0.5,
        }
    return {
        "org_offense_share": float(row.recent_offense_pick_share or 0.5),
        "org_defense_share": float(row.recent_defense_pick_share or 0.5),
        "org_trenches_share": float(row.recent_trenches_pick_share or 0.5),
        "org_need_follow_rate": float(row.recent_need_follow_rate or 0.5),
        "org_bpa_deviation_rate": float(row.recent_bpa_deviation_rate or 0.5),
        "regime_stability_score": float(row.regime_stability_score or 0.5),
    }
