"""Export research regressions as reusable draft-slot priors, and apply them.

A prior is a per-position linear model with its preprocessing spec, so a live
draft class can be scored without re-running the research:

    priors = json.loads(Path("backend/artifacts/draft_slot/position_priors.json").read_text())
    scored = score_prospects(prospects_df, priors, variant="athletic")

``prospects_df`` must carry the columns produced by ``features.add_features``
(position z-scores, drill-missing flags, pos_group, ...).

Variants:
- ``athletic``: combine + school tier, all invitees 2000+, target draft capital
  (-log pick, undrafted = 300). Works for any prospect with combine data.
- ``slot``: same plus age, drafted players only, target -log(pick).
- ``production``: ``slot`` plus position-specific college production, 2015+.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.app.draft_slot.design import DesignSpec, apply_design

VARIANTS = {
    "athletic": ("draft_capital", False),
    "slot": ("log_pick", False),
    "production": ("log_pick", True),
}
REFERENCE_YEAR = 2013  # draft_year_c = (draft_year - 2013) / 10 in the research fits


def build_priors(df: pd.DataFrame) -> dict[str, dict[str, dict[str, object]]]:
    from backend.app.draft_slot import analysis, config

    priors: dict[str, dict[str, dict[str, object]]] = {}
    for variant, (target, with_production) in VARIANTS.items():
        priors[variant] = {}
        for pos in config.POSITION_GROUPS:
            if with_production and pos not in analysis.PRODUCTION_FEATURES:
                continue
            sub = df[df["pos_group"] == pos]
            if with_production:
                sub = sub[sub["cfb_athlete_id"].notna()]
            fit = analysis.fit_regression(
                sub, analysis.model_features(pos, with_production), target
            )
            if fit is None:
                continue
            params = fit.model.params  # type: ignore[attr-defined]
            priors[variant][pos] = {
                "target": target,
                "n": fit.n,
                "r2": fit.r2,
                "intercept": float(params["const"]),
                "draft_year_coef": float(params["draft_year_c"]),
                "coefficients": {
                    row.feature: {"coef": float(row.coef), "p_value": float(row.p_value)}
                    for row in fit.table.itertuples()
                    if row.feature != "draft_year_c"
                },
                "spec": fit.spec.to_dict(),
            }
    return priors


def score_prospects(
    df: pd.DataFrame,
    priors: dict[str, dict[str, dict[str, object]]],
    variant: str = "athletic",
    max_p_value: float | None = None,
) -> pd.DataFrame:
    """Add ``prior_score`` (higher = earlier pick) and, for slot variants, ``prior_pick``.

    ``max_p_value`` zeroes out coefficients that were not significant in the research.
    """
    out = df.copy()
    out["prior_score"] = np.nan
    out["prior_pick"] = np.nan
    for pos, model in priors[variant].items():
        rows = out["pos_group"] == pos
        if not rows.any():
            continue
        spec = DesignSpec.from_dict(model["spec"])  # type: ignore[arg-type]
        X = apply_design(out.loc[rows], spec)
        coefs = model["coefficients"]  # type: ignore[assignment]
        score = pd.Series(0.0, index=X.index)
        for name, info in coefs.items():  # type: ignore[union-attr]
            if name not in X or (max_p_value is not None and info["p_value"] > max_p_value):
                continue
            score += info["coef"] * X[name]
        out.loc[rows, "prior_score"] = score
        if model["target"] == "log_pick":
            year_c = (out.loc[rows, "draft_year"] - REFERENCE_YEAR) / 10.0
            neg_log_pick = model["intercept"] + model["draft_year_coef"] * year_c + score
            out.loc[rows, "prior_pick"] = np.exp(-neg_log_pick).clip(1, 262)
    return out
