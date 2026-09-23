"""Statistical tests for which prospect traits predict draft slot.

Four complementary lenses, each run per position group:

1. Univariate screen: Spearman rank correlation of each trait with draft slot.
2. Multivariate regressions with HC3 robust errors:
   - OLS of log(pick) among drafted players (where in the draft),
   - logistic regression of drafted vs undrafted (whether drafted at all),
   - OLS of draft capital (-log pick, undrafted = pick 300) across all invitees.
3. Nested-model F-tests of feature groups (size, speed, explosion, ...), i.e. does a
   group add explanatory power once everything else is in the model.
4. Out-of-sample checks: leave-one-draft-year-out gradient boosting with grouped
   permutation importance, so conclusions do not rest on linear in-sample fits.

p-values are Benjamini-Hochberg adjusted within each table (``q_value``).

Leakage guard: birth dates come from the nflverse players table, which only
covers players who reached the NFL, so "age is missing" nearly means "went
undrafted". Age-derived features are therefore only used for the drafted-only
target, on complete cases (see ``DRAFTED_ONLY_FEATURES``).
Sign convention: every trait is oriented so that positive = better/bigger/faster,
and every target so that positive = drafted earlier. A positive coefficient
therefore means "more of this trait -> earlier pick".
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor
from statsmodels.stats.multitest import multipletests

from backend.app.draft_slot import config
from backend.app.draft_slot.design import NEGATE_FEATURES, DesignSpec, fit_design

# ---------------------------------------------------------------------------
# Feature definitions
# ---------------------------------------------------------------------------

ATHLETIC_FEATURES = [
    "z_height_in",
    "z_weight_lb",
    "z_forty",
    "z_bench",
    "z_vertical",
    "z_broad",
    "z_cone",
    "z_shuttle",
]
SKIP_FEATURES = [
    "forty_missing",
    "bench_missing",
    "vertical_missing",
    "broad_missing",
    "agility_missing",
]
CONTEXT_FEATURES = ["age_at_draft", "power_conf", "fbs"]

FEATURE_GROUPS: dict[str, list[str]] = {
    "size": ["z_height_in", "z_weight_lb"],
    "speed": ["z_forty"],
    "strength": ["z_bench"],
    "explosion": ["z_vertical", "z_broad"],
    "agility": ["z_cone", "z_shuttle"],
    "skipped_drills": SKIP_FEATURES,
    "age": ["age_at_draft"],
    "school_tier": ["power_conf", "fbs"],
}

# Position-specific college production (2015+ draft classes). Rates and shares only;
# see college_production for why raw totals are avoided.
PRODUCTION_FEATURES: dict[str, list[str]] = {
    "QB": [
        "final_pass_ypa",
        "final_pass_td_rate",
        "final_pass_int_rate",
        "final_pass_cmp_pct",
        "final_rush_ypg",
        "college_seasons",
    ],
    "RB": [
        "final_rush_ypg",
        "final_rush_ypc",
        "final_rush_yds_share",
        "final_rec_ypg",
        "final_total_td_per_game",
        "college_seasons",
    ],
    "WR": [
        "final_rec_yds_share",
        "final_dominator",
        "final_yds_per_target",
        "final_rec_ypr",
        "best_rec_yds_share",
        "college_seasons",
    ],
    "TE": [
        "final_rec_yds_share",
        "final_rec_ypg",
        "final_yds_per_target",
        "final_rec_ypr",
        "college_seasons",
    ],
    "EDGE": [
        "final_def_sacks_pg",
        "final_def_sack_share",
        "career_def_sacks_pg",
        "final_def_ff_pg",
        "final_def_pbu_pg",
        "college_seasons",
    ],
    "IDL": [
        "final_def_sacks_pg",
        "final_def_sack_share",
        "career_def_sacks_pg",
        "final_def_pbu_pg",
        "college_seasons",
    ],
    "LB": [
        "final_def_sacks_pg",
        "final_def_ball_production_pg",
        "final_def_ff_pg",
        "college_seasons",
    ],
    "CB": [
        "final_def_int_pg",
        "final_def_pbu_pg",
        "career_def_ball_production_pg",
        "college_seasons",
    ],
    "S": [
        "final_def_int_pg",
        "final_def_pbu_pg",
        "career_def_ball_production_pg",
        "final_def_sacks_pg",
        "college_seasons",
    ],
}

# Only observed (almost) exclusively for players who made the NFL; see module docstring.
DRAFTED_ONLY_FEATURES = {"age_at_draft", "breakout_age"}

TARGETS = {
    "log_pick": "OLS of -log(pick), drafted players only",
    "drafted": "Logit of drafted (1) vs undrafted (0)",
    "draft_capital": "OLS of -log(pick), undrafted = pick 300",
}


def model_features(pos_group: str, with_production: bool) -> list[str]:
    feats = [*ATHLETIC_FEATURES, *SKIP_FEATURES, *CONTEXT_FEATURES]
    if pos_group == "QB":
        # Quarterbacks essentially never bench at the combine; the few who do are outliers.
        feats = [f for f in feats if f not in {"z_bench", "bench_missing"}]
    if with_production:
        # Production comes from an FBS-games feed, so the FBS flag is ~constant there
        # and only produces separation artifacts.
        feats = [f for f in feats if f != "fbs"] + PRODUCTION_FEATURES.get(pos_group, [])
    return feats


def bh_adjust(p_values: pd.Series) -> pd.Series:
    """Benjamini-Hochberg q-values, leaving NaN p-values as NaN."""
    out = pd.Series(np.nan, index=p_values.index)
    ok = p_values.notna()
    if ok.any():
        out[ok] = multipletests(p_values[ok], method="fdr_bh")[1]
    return out


# ---------------------------------------------------------------------------
# 1. Univariate screen
# ---------------------------------------------------------------------------


def _orient(series: pd.Series, feat: str) -> pd.Series:
    return -series if feat in NEGATE_FEATURES else series


def univariate_screen(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pos in config.POSITION_GROUPS:
        sub = df[df["pos_group"] == pos]
        feats = [
            *ATHLETIC_FEATURES,
            "z_speed_score",
            "z_bmi",
            "athletic_composite",
            "drills_skipped",
            *CONTEXT_FEATURES,
            *PRODUCTION_FEATURES.get(pos, []),
            *(["breakout_age"] if pos == "WR" else []),
        ]
        for feat in feats:
            for target in ["log_pick", "draft_capital"]:
                if target != "log_pick" and feat in DRAFTED_ONLY_FEATURES:
                    continue
                data = sub if target == "draft_capital" else sub[sub["drafted"] == 1]
                y = -data["log_pick"] if target == "log_pick" else data["draft_capital"]
                x = _orient(data[feat].astype(float), feat)
                mask = x.notna() & y.notna()
                if mask.sum() < 30 or x[mask].nunique() < 2:
                    continue
                rho, p = stats.spearmanr(x[mask], y[mask])
                rows.append(
                    {
                        "pos_group": pos,
                        "feature": feat,
                        "target": target,
                        "n": int(mask.sum()),
                        "spearman_rho": rho,
                        "p_value": p,
                    }
                )
    out = pd.DataFrame(rows)
    out["q_value"] = bh_adjust(out["p_value"])
    return out


# ---------------------------------------------------------------------------
# 2. Multivariate regressions
# ---------------------------------------------------------------------------


@dataclass
class FitResult:
    table: pd.DataFrame
    n: int
    r2: float
    model: object
    spec: DesignSpec


def features_for_target(features: list[str], target: str) -> list[str]:
    if target == "log_pick":
        return features
    return [f for f in features if f not in DRAFTED_ONLY_FEATURES]


def _target_frame(
    df: pd.DataFrame, target: str, features: list[str] | None = None
) -> tuple[pd.DataFrame, pd.Series]:
    if target == "log_pick":
        data = df[df["drafted"] == 1]
        # Complete cases for age: missing birth dates cluster in short NFL careers.
        for feat in DRAFTED_ONLY_FEATURES & set(features or []):
            data = data[data[feat].notna()]
        return data, -data["log_pick"]
    if target == "drafted":
        return df, df["drafted"].astype(float)
    return df, df["draft_capital"]


def fit_regression(df: pd.DataFrame, features: list[str], target: str) -> FitResult | None:
    features = features_for_target(features, target)
    data, y = _target_frame(df, target, features)
    if len(data) < 60 or y.nunique() < 2:
        return None
    X, spec = fit_design(data, features)
    X = X.assign(draft_year_c=(data["draft_year"] - 2013) / 10.0)
    Xc = sm.add_constant(X, has_constant="add")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if target == "drafted":
            try:
                model = sm.Logit(y, Xc).fit(disp=0, cov_type="HC3", maxiter=200)
            except Exception:  # noqa: BLE001 - perfect separation on tiny groups
                model = sm.Logit(y, Xc).fit_regularized(disp=0, alpha=0.01)
            r2 = float(getattr(model, "prsquared", np.nan))
        else:
            model = sm.OLS(y, Xc).fit(cov_type="HC3")
            r2 = float(model.rsquared)
    table = pd.DataFrame(
        {"coef": model.params, "std_err": model.bse, "p_value": model.pvalues}
    ).drop(index=["const"])
    table.index.name = "feature"
    return FitResult(table=table.reset_index(), n=len(data), r2=r2, model=model, spec=spec)


def multivariate_tables(df: pd.DataFrame, with_production: bool) -> pd.DataFrame:
    frames = []
    for pos in config.POSITION_GROUPS:
        if with_production and pos not in PRODUCTION_FEATURES:
            continue
        sub = df[df["pos_group"] == pos]
        if with_production:
            sub = sub[sub["cfb_athlete_id"].notna()]
        feats = model_features(pos, with_production)
        for target in TARGETS:
            fit = fit_regression(sub, feats, target)
            if fit is None:
                continue
            frames.append(fit.table.assign(pos_group=pos, target=target, n=fit.n, r2=fit.r2))
    out = pd.concat(frames, ignore_index=True)
    out["q_value"] = np.nan
    for _, idx in out.groupby("target").groups.items():
        out.loc[idx, "q_value"] = bh_adjust(out.loc[idx, "p_value"])
    return out


# ---------------------------------------------------------------------------
# 3. Feature-group nested F-tests
# ---------------------------------------------------------------------------


def group_tests(df: pd.DataFrame, with_production: bool) -> pd.DataFrame:
    """Drop-one-group F-tests: partial R^2 and p-value for each feature group."""
    rows = []
    for pos in config.POSITION_GROUPS:
        if with_production and pos not in PRODUCTION_FEATURES:
            continue
        sub = df[df["pos_group"] == pos]
        if with_production:
            sub = sub[sub["cfb_athlete_id"].notna()]
        groups = dict(FEATURE_GROUPS)
        if with_production:
            groups["production"] = PRODUCTION_FEATURES[pos]
        for target in ["log_pick", "draft_capital"]:
            feats = features_for_target(model_features(pos, with_production), target)
            data, y = _target_frame(sub, target, feats)
            if len(data) < 60:
                continue
            X, _ = fit_design(data, feats)
            X = sm.add_constant(X.assign(draft_year_c=(data["draft_year"] - 2013) / 10.0))
            full = sm.OLS(y, X).fit()
            for name, members in groups.items():
                drop = [
                    c
                    for c in X.columns
                    if any(c == m or c == f"{m}_na" for m in members)
                    or (name == "skipped_drills" and c == "agility_missing")
                ]
                if not drop:
                    continue
                reduced = sm.OLS(y, X.drop(columns=drop)).fit()
                if reduced.df_resid <= full.df_resid:
                    continue  # dropped columns were collinear with the rest
                f_stat, p_value, _ = full.compare_f_test(reduced)
                partial_r2 = (reduced.ssr - full.ssr) / reduced.ssr
                rows.append(
                    {
                        "pos_group": pos,
                        "target": target,
                        "group": name,
                        "n": len(data),
                        "full_r2": full.rsquared,
                        "delta_r2": full.rsquared - reduced.rsquared,
                        "partial_r2": partial_r2,
                        "f_stat": f_stat,
                        "p_value": p_value,
                    }
                )
    out = pd.DataFrame(rows)
    out["q_value"] = bh_adjust(out["p_value"])
    return out


# ---------------------------------------------------------------------------
# 4. Out-of-sample: leave-one-year-out gradient boosting + grouped permutation
# ---------------------------------------------------------------------------


def _raw_design(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Unstandardized design for trees.

    Drill z-scores are filled at the position mean (0) so the "skipped drill"
    signal lives only in the ``*_missing`` flags and is attributed to that group
    by the permutation test. Other gaps stay NaN for the trees to route.
    """
    X = pd.DataFrame(index=df.index)
    for feat in features:
        if feat == "agility_missing":
            X[feat] = ((df["cone_missing"] + df["shuttle_missing"]) > 0).astype(float)
        elif feat.startswith("z_"):
            X[feat] = df[feat].astype(float).fillna(0.0)
        else:
            X[feat] = _orient(df[feat].astype(float), feat)
    return X.loc[:, X.nunique() > 1]


def out_of_sample(
    df: pd.DataFrame,
    with_production: bool,
    n_repeats: int = 5,
    seed: int = 7,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Leave-one-draft-year-out CV. Returns (fit summary, grouped permutation importance)."""
    rng = np.random.default_rng(seed)
    summaries, importances = [], []
    for pos in config.POSITION_GROUPS:
        if with_production and pos not in PRODUCTION_FEATURES:
            continue
        sub = df[df["pos_group"] == pos]
        if with_production:
            sub = sub[sub["cfb_athlete_id"].notna()]
        groups = dict(FEATURE_GROUPS)
        if with_production:
            groups["production"] = PRODUCTION_FEATURES[pos]
        feats = features_for_target(model_features(pos, with_production), "draft_capital")
        # The unified target keeps undrafted invitees in the sample.
        y = sub["draft_capital"].to_numpy()
        X = _raw_design(sub, feats)
        years = sub["draft_year"].to_numpy()
        preds = np.full(len(sub), np.nan)
        drop_scores: dict[str, list[float]] = {g: [] for g in groups}
        base_scores: list[float] = []
        for year in np.unique(years):
            test = years == year
            if test.sum() < 8 or (~test).sum() < 100:
                continue
            model = HistGradientBoostingRegressor(
                max_iter=250,
                learning_rate=0.05,
                max_depth=3,
                min_samples_leaf=20,
                l2_regularization=1.0,
                random_state=seed,
            )
            model.fit(X[~test], y[~test])
            Xt = X[test]
            preds[test] = model.predict(Xt)
            base = stats.spearmanr(preds[test], y[test])[0]
            base_scores.append(base)
            for name, members in groups.items():
                cols = [
                    c
                    for c in Xt.columns
                    if c in members or (name == "skipped_drills" and c == "agility_missing")
                ]
                if not cols:
                    continue
                losses = []
                for _ in range(n_repeats):
                    perm = Xt.copy()
                    idx = rng.permutation(len(perm))
                    perm[cols] = perm[cols].to_numpy()[idx]
                    losses.append(base - stats.spearmanr(model.predict(perm), y[test])[0])
                drop_scores[name].append(float(np.mean(losses)))
        mask = ~np.isnan(preds)
        if mask.sum() < 30:
            continue
        rho = stats.spearmanr(preds[mask], y[mask])[0]
        drafted = sub["drafted"].to_numpy()[mask] == 1
        rho_drafted = stats.spearmanr(preds[mask][drafted], y[mask][drafted])[0]
        summaries.append(
            {
                "pos_group": pos,
                "n": int(mask.sum()),
                "oos_spearman_all": rho,
                "oos_spearman_drafted": rho_drafted,
                "folds": len(base_scores),
            }
        )
        for name, vals in drop_scores.items():
            if not vals:
                continue
            arr = np.asarray(vals)
            # One-sided t-test across held-out years: is the importance > 0?
            t, p = stats.ttest_1samp(arr, 0.0)
            importances.append(
                {
                    "pos_group": pos,
                    "group": name,
                    "mean_spearman_drop": arr.mean(),
                    "se": arr.std(ddof=1) / np.sqrt(len(arr)),
                    "years_positive": float((arr > 0).mean()),
                    "p_value": p / 2 if t > 0 else 1 - p / 2,
                }
            )
    imp = pd.DataFrame(importances)
    if not imp.empty:
        imp["q_value"] = bh_adjust(imp["p_value"])
    return pd.DataFrame(summaries), imp


# ---------------------------------------------------------------------------
# 5. Era stability
# ---------------------------------------------------------------------------


def era_stability(df: pd.DataFrame, split_year: int = 2013) -> pd.DataFrame:
    """Compare log(pick) coefficients before vs from ``split_year`` (z-test on the gap)."""
    rows = []
    for pos in config.POSITION_GROUPS:
        sub = df[df["pos_group"] == pos]
        feats = model_features(pos, with_production=False)
        early = fit_regression(sub[sub["draft_year"] < split_year], feats, "log_pick")
        late = fit_regression(sub[sub["draft_year"] >= split_year], feats, "log_pick")
        if early is None or late is None:
            continue
        merged = early.table.merge(late.table, on="feature", suffixes=("_early", "_late"))
        merged["diff"] = merged["coef_late"] - merged["coef_early"]
        se = np.sqrt(merged["std_err_early"] ** 2 + merged["std_err_late"] ** 2)
        merged["p_value_diff"] = 2 * stats.norm.sf(np.abs(merged["diff"] / se))
        rows.append(merged.assign(pos_group=pos, n_early=early.n, n_late=late.n))
    out = pd.concat(rows, ignore_index=True)
    out["q_value_diff"] = bh_adjust(out["p_value_diff"])
    return out


def pooled_model(df: pd.DataFrame) -> pd.DataFrame:
    """All positions together with position fixed effects: league-wide predictors."""
    rows = []
    for target in TARGETS:
        feats = features_for_target([*ATHLETIC_FEATURES, *SKIP_FEATURES, *CONTEXT_FEATURES], target)
        data, y = _target_frame(df, target, feats)
        X, _ = fit_design(data, feats)
        dummies = pd.get_dummies(data["pos_group"], prefix="pos", drop_first=True, dtype=float)
        X = sm.add_constant(
            pd.concat([X, dummies], axis=1).assign(draft_year_c=(data["draft_year"] - 2013) / 10.0)
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = (
                sm.Logit(y, X).fit(disp=0, cov_type="HC3")
                if target == "drafted"
                else sm.OLS(y, X).fit(cov_type="HC3")
            )
        table = pd.DataFrame({"coef": model.params, "std_err": model.bse, "p_value": model.pvalues})
        table = table[~table.index.str.startswith("pos_") & (table.index != "const")]
        rows.append(table.rename_axis("feature").reset_index().assign(target=target, n=len(data)))
    out = pd.concat(rows, ignore_index=True)
    out["q_value"] = bh_adjust(out["p_value"])
    return out
