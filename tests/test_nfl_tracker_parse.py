from app.ingestion.nfl_com_tracker_live import _parse_tracker_picks

_MIN_HTML = """
\\"10402520-96bf-e9f2-4f68-8521ca896060\\",\\"abbreviation\\":\\"LV\\",\\"season\\":\\"2026\\"
\\"picks\\":[{\\"year\\":2026,\\"round\\":1,\\"pick\\":1,\\"overallPick\\":1,
\\"prospect\\":{\\"displayName\\":\\"Fernando Mendoza\\"},\\"pickIsIn\\":true,
\\"teamId\\":\\"10402520-96bf-e9f2-4f68-8521ca896060\\"},
{\\"year\\":2026,\\"round\\":1,\\"pick\\":2,\\"overallPick\\":2,\\"prospect\\":null,
\\"teamId\\":\\"10403430-1bc3-42c4-c7d8-39f38aed5f12\\"}]
\\"10403430-1bc3-42c4-c7d8-39f38aed5f12\\",\\"abbreviation\\":\\"NYJ\\",\\"season\\":\\"2026\\"
"""


def test_parse_tracker_picks_minimal() -> None:
    picks = _parse_tracker_picks(_MIN_HTML)
    assert len(picks) == 2
    assert picks[0].overall_pick == 1
    assert picks[0].team_abbreviation == "LV"
    assert picks[0].player_display_name == "Fernando Mendoza"
    assert picks[1].overall_pick == 2
    assert picks[1].player_display_name is None
