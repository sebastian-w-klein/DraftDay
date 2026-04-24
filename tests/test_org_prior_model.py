from backend.app.org_intelligence.models.org_prior_model import OrganizationalPriorModel


def test_org_prior_model_outputs_are_bounded() -> None:
    model = OrganizationalPriorModel()
    priors = model.infer_priors(
        {
            "gm_offense_bias": 0.7,
            "coach_offense_bias": 0.8,
            "org_offense_share": 0.6,
            "gm_trenches_bias": 0.65,
            "coach_trenches_bias": 0.55,
            "org_trenches_share": 0.5,
            "gm_need_follow_rate": 0.75,
            "org_need_follow_rate": 0.62,
            "gm_bpa_proxy_rate": 0.33,
            "org_bpa_deviation_rate": 0.41,
            "regime_stability_score": 0.89,
        }
    )
    assert 0.0 <= priors.offense_prior <= 1.0
    assert 0.0 <= priors.defense_prior <= 1.0
    assert 0.0 <= priors.trenches_prior <= 1.0
    assert 0.0 <= priors.skill_prior <= 1.0
