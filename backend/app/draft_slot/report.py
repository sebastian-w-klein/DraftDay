"""Render research results as Markdown tables."""

from __future__ import annotations

import pandas as pd

from backend.app.draft_slot import config

LABELS = {
    "z_height_in": "Height",
    "z_weight_lb": "Weight",
    "z_forty": "40-yard dash",
    "z_bench": "Bench reps",
    "z_vertical": "Vertical jump",
    "z_broad": "Broad jump",
    "z_cone": "3-cone",
    "z_shuttle": "Short shuttle",
    "z_speed_score": "Speed score",
    "z_bmi": "BMI",
    "athletic_composite": "Athletic composite",
    "drills_skipped": "# drills skipped",
    "forty_missing": "Skipped 40",
    "bench_missing": "Skipped bench",
    "vertical_missing": "Skipped vertical",
    "broad_missing": "Skipped broad",
    "agility_missing": "Skipped agility drills",
    "age_at_draft": "Age at draft (older)",
    "power_conf": "Power-conference school",
    "fbs": "FBS school",
    "draft_year_c": "Draft year (per decade)",
    "final_pass_ypa": "Final-yr pass Y/A",
    "final_pass_td_rate": "Final-yr TD rate",
    "final_pass_int_rate": "Final-yr INT rate (lower)",
    "final_pass_cmp_pct": "Final-yr comp %",
    "final_rush_ypg": "Final-yr rush Y/G",
    "final_rush_ypc": "Final-yr rush Y/C",
    "final_rush_yds_share": "Final-yr rush-yd share",
    "final_rec_ypg": "Final-yr rec Y/G",
    "final_total_td_per_game": "Final-yr TD/G",
    "final_rec_yds_share": "Final-yr rec-yd share",
    "final_dominator": "Final-yr dominator",
    "final_yds_per_target": "Final-yr Y/target",
    "final_rec_ypr": "Final-yr Y/rec",
    "best_rec_yds_share": "Best rec-yd share",
    "breakout_age": "Breakout age (younger)",
    "college_seasons": "College seasons (FBS)",
    "final_def_sacks_pg": "Final-yr sacks/G",
    "final_def_sack_share": "Final-yr team sack share",
    "career_def_sacks_pg": "Career sacks/G",
    "final_def_ff_pg": "Final-yr FF/G",
    "final_def_pbu_pg": "Final-yr PBU/G",
    "final_def_int_pg": "Final-yr INT/G",
    "final_def_ball_production_pg": "Final-yr (INT+PBU)/G",
    "career_def_ball_production_pg": "Career (INT+PBU)/G",
}


def label(feature: str) -> str:
    if feature.endswith("_na"):
        return f"{label(feature[:-3])} missing"
    return LABELS.get(feature, feature)


def stars(q: float) -> str:
    if pd.isna(q):
        return ""
    return "***" if q < 0.001 else "**" if q < 0.01 else "*" if q < 0.05 else ""


def _md_table(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")
    return "\n".join(lines)


def _positions(df: pd.DataFrame) -> list[str]:
    return [p for p in config.POSITION_GROUPS if p in set(df["pos_group"])]


def coverage_table(data: pd.DataFrame) -> str:
    rows = []
    for pos in _positions(data):
        sub = data[data["pos_group"] == pos]
        recent = sub[sub["draft_year"] >= config.FIRST_CFB_STATS_SEASON + 1]
        rows.append(
            {
                "Position": pos,
                "Invitees": len(sub),
                "Drafted": int(sub["drafted"].sum()),
                "Drafted %": f"{sub['drafted'].mean():.0%}",
                "Ran 40 %": f"{1 - sub['forty_missing'].mean():.0%}",
                "2015+ invitees": len(recent),
                "2015+ w/ production": (
                    f"{recent['cfb_athlete_id'].notna().mean():.0%}" if len(recent) else ""
                ),
            }
        )
    return _md_table(pd.DataFrame(rows))


def pooled_table(pooled: pd.DataFrame) -> str:
    wide = []
    for feature, grp in pooled.groupby("feature", sort=False):
        row = {"Predictor": label(feature)}
        for target, name in [
            ("log_pick", "Slot (drafted)"),
            ("drafted", "P(drafted) logit"),
            ("draft_capital", "Draft capital"),
        ]:
            hit = grp[grp["target"] == target]
            row[name] = (
                f"{hit['coef'].iloc[0]:+.3f}{stars(hit['q_value'].iloc[0])}" if len(hit) else "n/a"
            )
        wide.append(row)
    return _md_table(pd.DataFrame(wide))


def group_matrix(groups: pd.DataFrame, target: str, value: str = "partial_r2") -> str:
    sub = groups[groups["target"] == target]
    positions = _positions(sub)
    rows = []
    for group in sub["group"].unique():
        row = {"Feature group": group}
        for pos in positions:
            hit = sub[(sub["group"] == group) & (sub["pos_group"] == pos)]
            row[pos] = (
                f"{hit[value].iloc[0]:.3f}{stars(hit['q_value'].iloc[0])}" if len(hit) else ""
            )
        rows.append(row)
    n_row = {"Feature group": "_n_ / full R²"}
    for pos in positions:
        hit = sub[sub["pos_group"] == pos]
        n_row[pos] = f"{int(hit['n'].iloc[0])} / {hit['full_r2'].iloc[0]:.2f}"
    rows.append(n_row)
    return _md_table(pd.DataFrame(rows))


def importance_matrix(imp: pd.DataFrame) -> str:
    positions = _positions(imp)
    rows = []
    for group in imp["group"].unique():
        row = {"Feature group": group}
        for pos in positions:
            hit = imp[(imp["group"] == group) & (imp["pos_group"] == pos)]
            row[pos] = (
                f"{hit['mean_spearman_drop'].iloc[0]:.3f}{stars(hit['q_value'].iloc[0])}"
                if len(hit)
                else ""
            )
        rows.append(row)
    return _md_table(pd.DataFrame(rows))


def oos_table(summary: pd.DataFrame, summary_prod: pd.DataFrame) -> str:
    merged = summary.merge(summary_prod, on="pos_group", how="left", suffixes=("", "_prod"))
    out = pd.DataFrame(
        {
            "Position": merged["pos_group"],
            "Combine + school (2000+) ρ all": merged["oos_spearman_all"].map("{:.2f}".format),
            "ρ drafted only": merged["oos_spearman_drafted"].map("{:.2f}".format),
            "+ production (2015+) ρ all": merged["oos_spearman_all_prod"].map(
                lambda v: "" if pd.isna(v) else f"{v:.2f}"
            ),
            "ρ drafted only ": merged["oos_spearman_drafted_prod"].map(
                lambda v: "" if pd.isna(v) else f"{v:.2f}"
            ),
        }
    )
    return _md_table(out)


def significant_features(multi: pd.DataFrame, uni: pd.DataFrame, pos: str) -> str:
    rows = []
    sub = multi[(multi["pos_group"] == pos) & (multi["feature"] != "draft_year_c")]
    for feature, grp in sub.groupby("feature", sort=False):
        best_q = grp["q_value"].min()
        if pd.isna(best_q) or best_q >= 0.05:
            continue
        row = {"Predictor": label(feature)}
        for target, name in [
            ("log_pick", "Slot (drafted)"),
            ("drafted", "P(drafted)"),
            ("draft_capital", "Draft capital"),
        ]:
            hit = grp[grp["target"] == target]
            row[name] = (
                f"{hit['coef'].iloc[0]:+.2f}{stars(hit['q_value'].iloc[0])}" if len(hit) else "–"
            )
        u = uni[
            (uni["pos_group"] == pos) & (uni["feature"] == feature) & (uni["target"] == "log_pick")
        ]
        row["Univariate ρ (slot)"] = (
            f"{u['spearman_rho'].iloc[0]:+.2f}" f"{stars(u['q_value'].iloc[0])}" if len(u) else "–"
        )
        rows.append(row)
    if not rows:
        return "_No predictor survives FDR < 0.05._"
    return _md_table(pd.DataFrame(rows))


def production_table(multi: pd.DataFrame, uni: pd.DataFrame, pos: str) -> str:
    from backend.app.draft_slot.analysis import PRODUCTION_FEATURES

    features = PRODUCTION_FEATURES.get(pos, []) + (["breakout_age"] if pos == "WR" else [])
    rows = []
    for feature in features:
        row = {"Metric": label(feature)}
        for target, name in [("log_pick", "ρ slot"), ("draft_capital", "ρ capital")]:
            u = uni[
                (uni["pos_group"] == pos) & (uni["feature"] == feature) & (uni["target"] == target)
            ]
            row[name] = (
                f"{u['spearman_rho'].iloc[0]:+.2f}{stars(u['q_value'].iloc[0])}" if len(u) else "–"
            )
        for target, name in [("log_pick", "β slot"), ("draft_capital", "β capital")]:
            m = multi[
                (multi["pos_group"] == pos)
                & (multi["feature"] == feature)
                & (multi["target"] == target)
            ]
            row[name] = f"{m['coef'].iloc[0]:+.2f}{stars(m['q_value'].iloc[0])}" if len(m) else "–"
        rows.append(row)
    return _md_table(pd.DataFrame(rows))


def era_table(era: pd.DataFrame) -> str:
    hits = era[(era["q_value_diff"] < 0.05) & (era["feature"] != "draft_year_c")]
    if hits.empty:
        return "_No coefficient changed significantly between eras (FDR < 0.05)._"
    out = pd.DataFrame(
        {
            "Position": hits["pos_group"],
            "Predictor": hits["feature"].map(label),
            "2000–2012": hits["coef_early"].map("{:+.2f}".format),
            "2013+": hits["coef_late"].map("{:+.2f}".format),
            "q": hits["q_value_diff"].map("{:.3f}".format),
        }
    )
    return _md_table(out)


def render(results: dict[str, pd.DataFrame], data: pd.DataFrame) -> str:
    years = f"{int(data['draft_year'].min())}–{int(data['draft_year'].max())}"
    parts = [
        "# Draft-slot predictors: generated results",
        "",
        f"Generated by `python -m backend.app.draft_slot.cli`. Population: {len(data):,} NFL "
        f"Combine invitees, draft classes {years} (specialists excluded). College production "
        "covers the 2015+ classes. See `docs/draft-slot-predictors.md` for interpretation.",
        "",
        "Sign convention: every coefficient is oriented so **positive = drafted earlier / more "
        "likely drafted**. Traits are oriented so positive = bigger/faster/better (40, cone and "
        "shuttle times are sign-flipped). Continuous predictors are standardized (per 1 SD); "
        "flags are 0/1. Stars are Benjamini-Hochberg FDR q-values: * < 0.05, ** < 0.01, "
        "*** < 0.001. Regression errors are HC3 heteroskedasticity-robust.",
        "",
        "Targets: **Slot (drafted)** = OLS of −log(pick) among drafted players; "
        "**P(drafted)** = logit, drafted vs undrafted; **Draft capital** = OLS of −log(pick) "
        "with undrafted = pick 300. Age is only used for the drafted-only target (birth dates "
        "exist almost exclusively for players who reached the NFL).",
        "",
        "## Coverage",
        "",
        coverage_table(data),
        "",
        "## League-wide predictors (all positions, position fixed effects)",
        "",
        pooled_table(results["pooled"]),
        "",
        "## Which trait groups matter, by position",
        "",
        "Partial R² from drop-one-group nested F-tests, **Slot (drafted)**, 2000+:",
        "",
        group_matrix(results["groups"], "log_pick"),
        "",
        "Same, **Draft capital** (includes undrafted invitees; no age):",
        "",
        group_matrix(results["groups"], "draft_capital"),
        "",
        "With college production, **Slot (drafted)**, 2015+ classes with linked stats:",
        "",
        group_matrix(results["groups_prod"], "log_pick"),
        "",
        "## Out-of-sample check (leave-one-draft-year-out gradient boosting)",
        "",
        "Spearman ρ between held-out predictions and actual draft capital:",
        "",
        oos_table(results["oos_summary"], results["oos_summary_prod"]),
        "",
        "Grouped permutation importance (drop in held-out ρ when the group is shuffled; "
        "one-sided t-test across held-out years), combine + school, 2000+:",
        "",
        importance_matrix(results["oos_importance"]),
        "",
        "With college production, 2015+:",
        "",
        importance_matrix(results["oos_importance_prod"]),
        "",
        "## Era stability (Slot (drafted), 2000–2012 vs 2013+)",
        "",
        era_table(results["era"]),
        "",
        "## Significant individual predictors by position",
        "",
        "Multivariate coefficients (combine + school + age, 2000+) with FDR < 0.05 on at "
        "least one target, alongside the univariate Spearman ρ:",
        "",
    ]
    for pos in _positions(data):
        parts += [f"### {pos}", "", significant_features(results["multi"], results["uni"], pos), ""]
    parts += [
        "## College production predictors (2015+)",
        "",
        "Every production metric tested, with univariate Spearman ρ and the multivariate "
        "coefficient after controlling for combine, school tier and (for slot) age. "
        "Production metrics are collinear within a position, so the group F-test above is "
        "the better test of whether production matters at all; these rows show which "
        "metrics carry the signal.",
        "",
    ]
    for pos in _positions(results["multi_prod"]):
        parts += [
            f"### {pos}",
            "",
            production_table(results["multi_prod"], results["uni"], pos),
            "",
        ]
    return "\n".join(parts).rstrip() + "\n"
