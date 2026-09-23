"""Derived prospect features: position groups, composite athletic metrics,
position-relative z-scores, drill-skip indicators and draft-slot targets.

These builders are pure functions on a DataFrame so the prospect model in
``backend/app/ml`` can reuse them on a live draft class.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from backend.app.draft_slot import config

DRILLS = ["forty", "bench", "vertical", "broad", "cone", "shuttle"]
# Drills where a lower number is better; their z-scores are sign-flipped so that
# a positive z always means "better than the position average".
LOWER_IS_BETTER = {"forty", "cone", "shuttle"}
Z_METRICS = ["height_in", "weight_lb", "bmi", "speed_score", *DRILLS]


def assign_position_group(pos: str, weight: float) -> str | None:
    if pos in config.EXCLUDED_POSITIONS:
        return None
    # Weight splits resolve labels that mix roles across schemes and eras.
    if pos == "OLB":
        return "EDGE" if weight >= 243 else "LB"
    if pos == "DE" and weight >= 295:
        return "IDL"
    if pos == "DL":
        return "IDL" if weight >= 280 else "EDGE"
    return config.POSITION_GROUP_MAP.get(pos)


def add_position_zscores(df: pd.DataFrame, metrics: list[str] = Z_METRICS) -> pd.DataFrame:
    """Z-score each metric within position group (all years pooled)."""
    out = df.copy()
    grouped = out.groupby("pos_group")
    for metric in metrics:
        mean = grouped[metric].transform("mean")
        std = grouped[metric].transform("std").replace(0, np.nan)
        z = (out[metric] - mean) / std
        out[f"z_{metric}"] = -z if metric in LOWER_IS_BETTER else z
    return out


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["pos_group"] = [
        assign_position_group(p, w)
        for p, w in zip(out["pos"], out["weight_lb"].fillna(0), strict=True)
    ]
    out = out[out["pos_group"].notna()].copy()

    out["bmi"] = 703.0 * out["weight_lb"] / out["height_in"] ** 2
    # Bill Barnwell's speed score: weight-adjusted 40 time.
    out["speed_score"] = out["weight_lb"] * 200.0 / out["forty"] ** 4
    for drill in DRILLS:
        out[f"{drill}_missing"] = out[drill].isna().astype(int)
    out["drills_skipped"] = out[[f"{d}_missing" for d in DRILLS]].sum(axis=1)

    out = add_position_zscores(out)
    out["z_explosion"] = out[["z_vertical", "z_broad"]].mean(axis=1)
    out["z_agility"] = out[["z_cone", "z_shuttle"]].mean(axis=1)
    out["athletic_composite"] = out[[f"z_{d}" for d in DRILLS]].mean(axis=1)

    # Targets. log(pick) spreads early picks, where value changes fastest.
    out["log_pick"] = np.log(out["overall_pick"])
    out["pick_or_undrafted"] = out["overall_pick"].fillna(config.UNDRAFTED_PICK)
    out["draft_capital"] = -np.log(out["pick_or_undrafted"])
    out["round1"] = (out["overall_pick"] <= 32).astype(int)
    return out
