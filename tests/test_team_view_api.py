from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.session import get_db
from backend.app.org_intelligence.routes.team_view_routes import router


def _build_app() -> TestClient:
    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield None

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_org_profile_route_shape(monkeypatch) -> None:
    client = _build_app()

    def fake_org_profile(db, team_abbr, year):  # noqa: ANN001
        return {
            "team": team_abbr,
            "year": year,
            "gm_profile": {"name": "GM"},
            "hc_profile": {"name": "HC"},
            "regime_stability_score": 0.7,
            "historical_tendency_metrics": {"offense_prior": 0.6},
            "favored_positions_groups": {"gm": ["OT"], "hc": ["EDGE"]},
        }

    monkeypatch.setattr(
        "backend.app.org_intelligence.routes.team_view_routes.get_org_profile",
        fake_org_profile,
    )
    resp = client.get("/api/v1/team-view/org-profile?team=TEN&year=2026")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["team"] == "TEN"
    assert "historical_tendency_metrics" in payload


def test_position_probs_route_shape(monkeypatch) -> None:
    client = _build_app()

    def fake_probs(db, team_abbr, pick, year):  # noqa: ANN001
        return {
            "team": team_abbr,
            "year": year,
            "pick": pick,
            "base_ml_position_probabilities": {"OT": 0.3},
            "org_adjusted_position_probabilities": {"OT": 0.4},
            "delta_by_position": {"OT": 0.1},
            "team_snapshot": {"team_name": "Titans"},
        }

    monkeypatch.setattr(
        "backend.app.org_intelligence.routes.team_view_routes.get_org_adjusted_position_probs",
        fake_probs,
    )
    resp = client.get("/api/v1/team-view/position-probs?team=TEN&year=2026&pick=1")
    assert resp.status_code == 200
    payload = resp.json()
    assert "org_adjusted_position_probabilities" in payload


def test_player_probs_route_shape(monkeypatch) -> None:
    client = _build_app()

    def fake_player_probs(db, team_abbr, pick, year, candidate_players, **_kwargs):  # noqa: ANN001
        return {
            "team": team_abbr,
            "year": year,
            "pick": pick,
            "ranked_players": [
                {
                    "player_name": "Cam Ward",
                    "position": "QB",
                    "base_probability": 0.42,
                    "org_adjusted_probability": 0.47,
                    "need_component": 0.78,
                    "talent_component": 0.84,
                    "context_component": 0.63,
                    "organizational_component": 0.69,
                }
            ],
            "integrated_explanation": "Need and org priors align on QB.",
        }

    monkeypatch.setattr(
        "backend.app.org_intelligence.routes.team_view_routes.get_org_adjusted_player_probs",
        fake_player_probs,
    )
    resp = client.post(
        "/api/v1/team-view/player-probs",
        json={
            "team": "TEN",
            "year": 2026,
            "pick": 1,
            "candidate_players": [
                {
                    "player_name": "Cam Ward",
                    "position": "QB",
                    "prospect_score": 0.88,
                    "superstar_potential_score": 0.82,
                    "consensus_rank": 1,
                }
            ],
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "ranked_players" in payload
    assert "organizational_component" in payload["ranked_players"][0]
    assert "integrated_explanation" in payload


def test_team_summary_route_shape(monkeypatch) -> None:
    client = _build_app()

    def fake_summary(db, team_abbr, year, pick, **_kwargs):  # noqa: ANN001
        return {
            "team": team_abbr,
            "year": year,
            "pick": pick,
            "team_snapshot": {"team_name": "Titans"},
            "org_summary": {"regime_stability_score": 0.71},
            "consensus_top_players": [{"player_name": "Cam Ward", "weighted_probability": 0.5}],
            "ml_top_players": [{"player_name": "Cam Ward", "probability": 0.45}],
            "org_adjusted_top_players": [
                {"player_name": "Cam Ward", "org_adjusted_probability": 0.5, "organizational_component": 0.6}
            ],
            "top_position_predictions": {"QB": 0.42},
            "integrated_explanation": "Team need and organizational priors reinforce QB.",
        }

    monkeypatch.setattr(
        "backend.app.org_intelligence.routes.team_view_routes.get_team_view_summary",
        fake_summary,
    )
    resp = client.get("/api/v1/team-view/summary?team=TEN&year=2026&pick=1")
    assert resp.status_code == 200
    payload = resp.json()
    assert "org_adjusted_top_players" in payload
    assert "integrated_explanation" in payload


def test_team_view_backtest_route_shape() -> None:
    client = _build_app()
    resp = client.get("/api/v1/team-view/backtest")
    assert resp.status_code == 200
    payload = resp.json()
    assert "comparison" in payload
    assert "consensus_ml_org_ensemble" in payload["comparison"]
