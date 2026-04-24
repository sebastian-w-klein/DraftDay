from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


@dataclass
class PositionModelBundle:
    pipeline: Pipeline
    class_labels: list[str]
    version: str


class PositionModel:
    version = "position-logreg-v1"

    def train(self, rows: list[dict[str, float | str | int]]) -> PositionModelBundle:
        if not rows:
            raise ValueError("No training rows supplied")
        X = [
            {
                "need_score": float(r["need_score"]),
                "board_scarcity_score": float(r["board_scarcity_score"]),
                "best_available_player_score": float(r["best_available_player_score"]),
                "overall_pick": float(r["overall_pick"]),
                "round_number": float(r["round_number"]),
                "top_need_position": str(r["top_need_position"] or "UNK"),
            }
            for r in rows
        ]
        y = [str(r["label_position"]) for r in rows]

        model = LogisticRegression(max_iter=600)
        pipeline = Pipeline(
            steps=[
                ("vectorizer", DictVectorizer(sparse=True)),
                ("scaler", StandardScaler(with_mean=False)),
                ("model", model),
            ]
        )
        pipeline.fit(X, y)
        classes = list(np.array(pipeline.named_steps["model"].classes_).astype(str))
        return PositionModelBundle(pipeline=pipeline, class_labels=classes, version=self.version)

    def predict_proba(
        self, bundle: PositionModelBundle, row: dict[str, float | str | int]
    ) -> dict[str, float]:
        payload = [
            {
                "need_score": float(row["need_score"]),
                "board_scarcity_score": float(row["board_scarcity_score"]),
                "best_available_player_score": float(row["best_available_player_score"]),
                "overall_pick": float(row["overall_pick"]),
                "round_number": float(row["round_number"]),
                "top_need_position": str(row.get("top_need_position") or "UNK"),
            }
        ]
        probs = bundle.pipeline.predict_proba(payload)[0]
        return {label: float(prob) for label, prob in zip(bundle.class_labels, probs)}
