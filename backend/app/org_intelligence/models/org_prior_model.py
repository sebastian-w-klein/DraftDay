from dataclasses import dataclass


@dataclass
class OrganizationalPriors:
    offense_prior: float
    defense_prior: float
    trenches_prior: float
    skill_prior: float
    need_follow_prior: float
    bpa_deviation_prior: float
    regime_stability_adjustment: float


class OrganizationalPriorModel:
    version = "org-prior-v1"

    def infer_priors(self, features: dict[str, float]) -> OrganizationalPriors:
        gm_off = features.get("gm_offense_bias", 0.5)
        coach_off = features.get("coach_offense_bias", 0.5)
        org_off = features.get("org_offense_share", 0.5)
        offense_prior = _clip((gm_off + coach_off + org_off) / 3.0)
        defense_prior = _clip(1.0 - offense_prior)

        gm_trench = features.get("gm_trenches_bias", 0.5)
        coach_trench = features.get("coach_trenches_bias", 0.5)
        org_trench = features.get("org_trenches_share", 0.5)
        trenches_prior = _clip((gm_trench + coach_trench + org_trench) / 3.0)
        skill_prior = _clip(1.0 - trenches_prior)

        need_follow = _clip((features.get("gm_need_follow_rate", 0.5) + features.get("org_need_follow_rate", 0.5)) / 2.0)
        bpa = _clip((features.get("gm_bpa_proxy_rate", 0.5) + features.get("org_bpa_deviation_rate", 0.5)) / 2.0)
        stability = _clip(features.get("regime_stability_score", 0.5))
        return OrganizationalPriors(
            offense_prior=offense_prior,
            defense_prior=defense_prior,
            trenches_prior=trenches_prior,
            skill_prior=skill_prior,
            need_follow_prior=need_follow,
            bpa_deviation_prior=bpa,
            regime_stability_adjustment=stability,
        )


def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))
