import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.test_nfl_tracker_parse import test_parse_tracker_picks_minimal  # noqa: E402

if __name__ == "__main__":
    test_parse_tracker_picks_minimal()
    print("ok")
