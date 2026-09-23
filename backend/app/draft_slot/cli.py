"""Run the draft-slot predictor research end to end.

Usage:
  python -m backend.app.draft_slot.cli                # use cached downloads when present
  python -m backend.app.draft_slot.cli --refresh      # re-download all sources
  python -m backend.app.draft_slot.cli --skip-oos     # skip the slow CV step (reuses last run's)

Writes to backend/artifacts/draft_slot/:
  report.md               generated tables
  position_priors.json    per-position linear priors (see priors.py)
  *.csv                   every result table
The joined prospect table is cached at data/draft_slot/processed/prospects.parquet.
"""

from __future__ import annotations

import argparse
import json
import warnings

import pandas as pd

from backend.app.draft_slot import analysis, config, priors, report
from backend.app.draft_slot.dataset import build_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--refresh", action="store_true", help="Re-download source data.")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild the prospect table.")
    parser.add_argument("--skip-oos", action="store_true", help="Skip out-of-sample CV.")
    parser.add_argument("--permutation-repeats", type=int, default=5)
    args = parser.parse_args()
    warnings.filterwarnings("ignore")

    cache = config.PROCESSED_DIR / "prospects.parquet"
    if cache.exists() and not (args.refresh or args.rebuild):
        data = pd.read_parquet(cache)
    else:
        print("Building prospect table...")
        data = build_dataset(refresh=args.refresh)
        cache.parent.mkdir(parents=True, exist_ok=True)
        data.to_parquet(cache)
    print(
        f"{len(data):,} prospects, draft classes "
        f"{int(data['draft_year'].min())}-{int(data['draft_year'].max())}"
    )

    results: dict[str, pd.DataFrame] = {}
    print("Univariate screen...")
    results["uni"] = analysis.univariate_screen(data)
    print("Multivariate regressions...")
    results["pooled"] = analysis.pooled_model(data)
    results["multi"] = analysis.multivariate_tables(data, with_production=False)
    results["multi_prod"] = analysis.multivariate_tables(data, with_production=True)
    print("Feature-group F-tests...")
    results["groups"] = analysis.group_tests(data, with_production=False)
    results["groups_prod"] = analysis.group_tests(data, with_production=True)
    print("Era stability...")
    results["era"] = analysis.era_stability(data)
    empty_summary = pd.DataFrame(
        columns=["pos_group", "n", "oos_spearman_all", "oos_spearman_drafted", "folds"]
    )
    empty_imp = pd.DataFrame(columns=["pos_group", "group", "mean_spearman_drop", "q_value"])
    if args.skip_oos:
        # Reuse the last full run's out-of-sample tables when they exist.
        for name, empty in [
            ("oos_summary", empty_summary),
            ("oos_summary_prod", empty_summary),
            ("oos_importance", empty_imp),
            ("oos_importance_prod", empty_imp),
        ]:
            path = config.ARTIFACT_DIR / f"{name}.csv"
            results[name] = pd.read_csv(path) if path.exists() else empty
    else:
        print("Out-of-sample CV (leave one draft year out)...")
        results["oos_summary"], results["oos_importance"] = analysis.out_of_sample(
            data, with_production=False, n_repeats=args.permutation_repeats
        )
        results["oos_summary_prod"], results["oos_importance_prod"] = analysis.out_of_sample(
            data, with_production=True, n_repeats=args.permutation_repeats
        )

    out_dir = config.ARTIFACT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in results.items():
        frame.to_csv(out_dir / f"{name}.csv", index=False, float_format="%.6g")
    (out_dir / "report.md").write_text(report.render(results, data), encoding="utf-8")
    (out_dir / "position_priors.json").write_text(
        json.dumps(priors.build_priors(data), indent=1), encoding="utf-8"
    )
    print(f"Wrote results to {out_dir}")


if __name__ == "__main__":
    main()
