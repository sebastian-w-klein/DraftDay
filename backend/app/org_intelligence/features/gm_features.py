from backend.app.org_intelligence.data.gm_loader import GmProfileRow


def gm_feature_vector(row: GmProfileRow | None) -> dict[str, float]:
    if row is None:
        return {
            "gm_offense_bias": 0.5,
            "gm_defense_bias": 0.5,
            "gm_trenches_bias": 0.5,
            "gm_need_follow_rate": 0.5,
            "gm_bpa_proxy_rate": 0.5,
        }
    return {
        "gm_offense_bias": row.offense_share,
        "gm_defense_bias": row.defense_share,
        "gm_trenches_bias": row.trenches_share,
        "gm_need_follow_rate": row.need_follow_rate,
        "gm_bpa_proxy_rate": row.bpa_proxy_rate,
    }
