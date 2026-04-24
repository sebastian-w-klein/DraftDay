import json
from types import SimpleNamespace

from backend.app.org_intelligence.inference.org_predictor import _candidate_signature, _read_team_view_cache


class _FakeDb:
    def __init__(self, payload: dict[str, object] | None):
        self.payload = payload

    def scalar(self, _query):  # noqa: ANN001
        if self.payload is None:
            return None
        return SimpleNamespace(payload_json=json.dumps(self.payload))


def test_read_team_view_cache_returns_payload() -> None:
    db = _FakeDb({"team": "TEN", "year": 2026})
    payload = _read_team_view_cache(db, cycle_id=1, team_id=1, overall_pick=1, model_version="team-view-position-v1")
    assert payload is not None
    assert payload["team"] == "TEN"


def test_read_team_view_cache_returns_none_when_missing() -> None:
    db = _FakeDb(None)
    payload = _read_team_view_cache(db, cycle_id=1, team_id=1, overall_pick=1, model_version="team-view-position-v1")
    assert payload is None


def test_candidate_signature_changes_when_players_change() -> None:
    a = _candidate_signature(
        [
            {"player_name": "Cam Ward", "position": "QB", "consensus_rank": 1},
            {"player_name": "Travis Hunter", "position": "CB", "consensus_rank": 2},
        ]
    )
    b = _candidate_signature(
        [
            {"player_name": "Cam Ward", "position": "QB", "consensus_rank": 1},
            {"player_name": "Will Campbell", "position": "OT", "consensus_rank": 5},
        ]
    )
    assert a != b
