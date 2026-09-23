"""Regression design matrices with recorded preprocessing.

``fit_design`` orients, imputes and standardizes features and returns a
``DesignSpec`` describing exactly what it did; ``apply_design`` replays that spec
on new rows (e.g. a live draft class), so coefficients fitted in the research can
be applied unchanged by a prediction model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

# Oriented so positive = "better": fewer interceptions, younger breakout.
NEGATE_FEATURES = {"final_pass_int_rate", "breakout_age"}
# Share of missing values above which a feature also gets an ``<name>_na`` flag.
NA_FLAG_THRESHOLD = 0.02


@dataclass
class ColumnSpec:
    name: str
    source: str
    negate: bool = False
    fill: float = 0.0
    mean: float = 0.0
    sd: float = 1.0
    is_na_flag: bool = False
    standardize: bool = True


@dataclass
class DesignSpec:
    columns: list[ColumnSpec] = field(default_factory=list)

    @property
    def names(self) -> list[str]:
        return [c.name for c in self.columns]

    def to_dict(self) -> dict[str, list[dict[str, object]]]:
        return {"columns": [asdict(c) for c in self.columns]}

    @classmethod
    def from_dict(cls, payload: dict[str, list[dict[str, object]]]) -> DesignSpec:
        return cls(columns=[ColumnSpec(**c) for c in payload["columns"]])  # type: ignore[arg-type]


def _source(df: pd.DataFrame, feat: str) -> pd.Series:
    if feat == "agility_missing":
        return ((df["cone_missing"] + df["shuttle_missing"]) > 0).astype(float)
    col = df[feat].astype(float)
    return -col if feat in NEGATE_FEATURES else col


def fit_design(df: pd.DataFrame, features: list[str]) -> tuple[pd.DataFrame, DesignSpec]:
    """Build the regression design and the spec that reproduces it.

    Drill z-scores are imputed at 0 (position mean); the matching ``*_missing``
    flag carries the "skipped this drill" signal. Other features are imputed at
    the median, with their own ``_na`` flag when more than 2% are missing.
    Continuous columns are standardized so coefficients read as "effect of a
    1 SD change"; binary columns are left as 0/1. Constant columns are dropped.
    """
    specs: list[ColumnSpec] = []
    for feat in features:
        col = _source(df, feat)
        negate = feat in NEGATE_FEATURES
        if feat.startswith("z_"):
            fill = 0.0
        else:
            fill = float(col.median()) if col.notna().any() else 0.0
            if col.isna().mean() > NA_FLAG_THRESHOLD:
                specs.append(
                    ColumnSpec(name=f"{feat}_na", source=feat, is_na_flag=True, standardize=False)
                )
        filled = col.fillna(fill)
        binary = set(filled.unique()) <= {0.0, 1.0}
        specs.append(
            ColumnSpec(
                name=feat,
                source=feat,
                negate=negate,
                fill=fill,
                mean=0.0 if binary else float(filled.mean()),
                sd=1.0 if binary else float(filled.std() or 1.0),
                standardize=not binary,
            )
        )
    spec = DesignSpec(columns=specs)
    X = apply_design(df, spec)
    keep = [c for c in spec.columns if X[c.name].std() > 0]
    spec = DesignSpec(columns=keep)
    return X[spec.names], spec


def apply_design(df: pd.DataFrame, spec: DesignSpec) -> pd.DataFrame:
    X = pd.DataFrame(index=df.index)
    for c in spec.columns:
        raw = df[c.source].astype(float) if c.source in df else pd.Series(np.nan, index=df.index)
        if c.source == "agility_missing":
            raw = _source(df, "agility_missing")
        if c.is_na_flag:
            X[c.name] = raw.isna().astype(float)
            continue
        col = (-raw if c.negate else raw).fillna(c.fill)
        X[c.name] = (col - c.mean) / c.sd if c.standardize else col
    return X
