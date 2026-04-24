from backend.app.org_intelligence.features.coach_features import coach_feature_vector
from backend.app.org_intelligence.features.gm_features import gm_feature_vector
from backend.app.org_intelligence.features.org_tendency_features import org_tendency_feature_vector


def assemble_team_view_features(
    gm_row,  # noqa: ANN001
    coach_row,  # noqa: ANN001
    org_row,  # noqa: ANN001
) -> dict[str, float]:
    features = {}
    features.update(gm_feature_vector(gm_row))
    features.update(coach_feature_vector(coach_row))
    features.update(org_tendency_feature_vector(org_row))
    return features
