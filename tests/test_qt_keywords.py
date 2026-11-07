"""Qt objects are set up with setters, not property keywords (QTimer(interval=…)): the packaged 0.3.11 refused
them ("'interval' is not a Qt property or a signal") and every finished task raised in the window."""

import re
from pathlib import Path

SRC = Path(__file__).parents[1] / "src" / "astrowb"
KEYWORDS = re.compile(r"\bQ[A-Z]\w+\([^()]*\b(interval|singleShot|timeout|clicked|toggled|triggered|objectName)=")


def test_no_property_keywords_in_qt_constructors():
    found = []
    for p in SRC.rglob("*.py"):
        lines = p.read_text(encoding="utf-8").splitlines()
        found += [f"{p.relative_to(SRC)}:{n}" for n, line in enumerate(lines, 1) if KEYWORDS.search(line)]
    assert not found, found
