from backend.app.org_intelligence.models.org_prior_model import OrganizationalPriors


class IntegratedTeamPredictionModel:
    version = "team-integrated-v1"

    def adjust_position_probabilities(
        self,
        base_probs: dict[str, float],
        priors: OrganizationalPriors,
    ) -> dict[str, float]:
        adjusted: dict[str, float] = {}
        for position, prob in base_probs.items():
            modifier = 1.0
            if position in {"OT", "IOL", "C", "G", "EDGE", "DT"}:
                modifier += (priors.trenches_prior - 0.5) * 0.6
            if position in {"WR", "RB", "TE", "QB", "CB", "S"}:
                modifier += (priors.skill_prior - 0.5) * 0.4
            if position in {"QB", "RB", "WR", "TE", "OT", "IOL", "C", "G"}:
                modifier += (priors.offense_prior - 0.5) * 0.5
            else:
                modifier += (priors.defense_prior - 0.5) * 0.5
            adjusted[position] = max(0.0, prob * modifier)

        total = sum(adjusted.values()) or 1.0
        return {k: v / total for k, v in sorted(adjusted.items(), key=lambda item: item[1], reverse=True)}
