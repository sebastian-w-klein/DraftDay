from app.normalization.normalizers import normalize_player_name, normalize_position, normalize_school


def test_normalize_player_name_suffix() -> None:
    assert normalize_player_name("Will Johnson Jr.") == "will johnson"


def test_normalize_position() -> None:
    assert normalize_position("de") == "EDGE"


def test_normalize_school_alias() -> None:
    assert normalize_school("Ohio St.") == "ohio state"
