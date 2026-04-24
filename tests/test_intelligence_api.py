from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.session import get_db
from backend.app.ml.routes.intelligence_routes import router


def test_pick_player_probs_endpoint_response_shape(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router)
    def override_get_db():
        yield None
    app.dependency_overrides[get_db] = override_get_db

    def fake_predict_pick_players(db, team_abbr, pick, year, candidate_payload, **_kwargs):  # noqa: ANN001
        return SimpleNamespace(
            team=team_abbr.upper(),
            overall_pick=pick,
            year=year,
            model_version="player-logreg-v1",
            ranked_players=[
                SimpleNamespace(
                    player_name="Travis Hunter",
                    position="CB",
                    probability=0.63,
                    need_component=0.31,
                    talent_component=0.94,
                    context_component=0.76,
                    superstar_override_score=0.57,
                )
            ],
            explanation_summary={"candidate_count": 1, "top_need_position": "QB"},
        )

    monkeypatch.setattr(
        "backend.app.ml.routes.intelligence_routes.predict_pick_players",
        fake_predict_pick_players,
    )
    client = TestClient(app)
    response = client.post(
        "/api/v1/intelligence/pick-player-probs",
        json={
            "team": "TEN",
            "pick": 1,
            "year": 2026,
            "candidate_players": [
                {
                    "player_name": "Travis Hunter",
                    "position": "CB",
                    "prospect_score": 0.94,
                    "superstar_potential_score": 0.95,
                    "consensus_rank": 2,
                }
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["team"] == "TEN"
    assert payload["ranked_players"][0]["player_name"] == "Travis Hunter"
    assert "superstar_override_score" in payload["ranked_players"][0]


def test_compare_with_consensus_payload_contains_grouped_explanations(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield None

    app.dependency_overrides[get_db] = override_get_db

    def fake_compare(db, team_abbr, pick, year, **_kwargs):  # noqa: ANN001
        return SimpleNamespace(
            team=team_abbr.upper(),
            overall_pick=pick,
            year=year,
            consensus_top_players=[{"player_name": "Cam Ward", "weighted_probability": 0.51}],
            ml_top_players=[{"player_name": "Travis Hunter", "probability": 0.49}],
            overlap=[],
            disagreement_score=0.8,
            divergence_explanation={
                "need_component": 0.31,
                "talent_component": 0.82,
                "context_component": 0.44,
            },
        )

    monkeypatch.setattr(
        "backend.app.ml.routes.intelligence_routes.compare_with_consensus",
        fake_compare,
    )
    client = TestClient(app)
    response = client.get("/api/v1/intelligence/compare-with-consensus?team=TEN&pick=1&year=2026")
    assert response.status_code == 200
    payload = response.json()
    assert "divergence_explanation" in payload
    assert "need_component" in payload["divergence_explanation"]
    assert "talent_component" in payload["divergence_explanation"]
    assert "context_component" in payload["divergence_explanation"]
