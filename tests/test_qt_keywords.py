"""Qt objects are set up with setters, not property keywords (QTimer(interval=…)): the packaged 0.3.11 refused
them ("'interval' is not a Qt property or a signal") and every finished task raised in the window."""

import ast
from pathlib import Path

SRC = Path(__file__).parents[1] / "src" / "astrowb"


def test_no_property_keywords_in_qt_constructors():
    found = []
    for p in SRC.rglob("*.py"):
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if not isinstance(n, ast.Call):
                continue
            name = getattr(n.func, "id", None) or getattr(n.func, "attr", "")
            bad = [k.arg for k in n.keywords if k.arg != "parent"]  # parent is a real argument, not a property
            if name[:1] == "Q" and name[1:2].isupper() and bad:
                found.append(f"{p.relative_to(SRC)}:{n.lineno} {name}({', '.join(map(str, bad))}=)")
    assert not found, found
