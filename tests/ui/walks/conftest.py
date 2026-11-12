import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import Harness  # noqa: E402


@pytest.fixture
def walk(qtbot, tmp_path):
    """walk(lang) -> a Harness on the real main window; closed after the test."""
    made = []

    def start(lang="en"):
        made.append(Harness(qtbot, tmp_path, lang))
        return made[-1]

    yield start
    for h in made:
        h.close()
