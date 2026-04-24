from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


@dataclass
class PlayerModelBundle:
    pipeline: Pipeline
    version: str


class PlayerModel:
    version = "player-logreg-v1"

    def train(self, rows: list[dict[str, float | str | int | bool | None]]) -> PlayerModelBundle:
        if not rows:
            raise ValueError("No rows supplied for player model training")
        X = [self._to_feature_payload(row) for row in rows]
        y = [1 if bool(row.get("selected_label")) else 0 for row in rows]
        if len(set(y)) < 2:
            # Keep training pipeline runnable in sparse demo datasets by injecting one counterexample.
            synthetic = dict(rows[0])
            synthetic["selected_label"] = not bool(rows[0].get("selected_label"))
            rows = [*rows, synthetic]
            X = [self._to_feature_payload(row) for row in rows]
            y = [1 if bool(row.get("selected_label")) else 0 for row in rows]

        pipeline = Pipeline(
            steps=[
                ("vectorizer", DictVectorizer(sparse=True)),
                ("scaler", StandardScaler(with_mean=False)),
                ("model", LogisticRegression(max_iter=800)),
            ]
        )
        pipeline.fit(X, np.array(y, dtype=int))
        return PlayerModelBundle(pipeline=pipeline, version=self.version)

    def predict_proba(
        self,
        bundle: PlayerModelBundle,
        rows: list[dict[str, float | str | int | bool | None]],
    ) -> list[float]:
        payloads = [self._to_feature_payload(row) for row in rows]
        probs = bundle.pipeline.predict_proba(payloads)[:, 1]
        return [float(prob) for prob in probs]

    def _to_feature_payload(self, row: dict[str, float | str | int | bool | None]) -> dict[str, float | str]:
        return {
            "team_need_score": float(row.get("team_need_score", 0)),
            "prospect_score": float(row.get("prospect_score", 0)),
            "superstar_potential_score": float(row.get("superstar_potential_score", 0)),
            "positional_scarcity_score": float(row.get("positional_scarcity_score", 0)),
            "consensus_rank": float(row.get("consensus_rank", 300) or 300),
            "rank_gap_from_best_available": float(row.get("rank_gap_from_best_available", 0)),
            "rank_gap_within_position": float(row.get("rank_gap_within_position", 0)),
            "fit_gap": float(row.get("fit_gap", 0)),
            "need_vs_bpa_gap": float(row.get("need_vs_bpa_gap", 0)),
            "position": str(row.get("position", "UNK")),
        }
