"""UI-1: colours come from kit/tokens.py; text is readable on every surface; no new colour literals in ui/."""

import json
import re
from pathlib import Path

import pytest

from astrowb.ui.kit import tokens

UI = Path(__file__).parents[1] / "src" / "astrowb" / "ui"
ALLOWED = json.loads((Path(__file__).parent / "data" / "colour_literals.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["dark", "light"])
def test_text_is_readable_on_every_surface(name):
    t = tokens.theme(name)
    for surface in ("surface.0", "surface.1", "surface.2", "surface.3"):
        for text, least in (("text", 4.5), ("text.muted", 4.5), ("text.faint", 2.5)):
            assert tokens.contrast(t[text], t[surface]) >= least, (name, text, surface)
    assert tokens.contrast(t["on.accent"], t["accent"]) >= 3.0  # buttons' text: large / bold UI text


def test_no_new_colour_literals_outside_the_tokens():
    """A colour written in ui/ is a token not used: the count per file may only fall (UI-16 removes the rest)."""
    for path in UI.rglob("*.py"):
        rel = path.relative_to(UI).as_posix()
        if rel == "kit/tokens.py":
            continue
        n = len(re.findall(r"#[0-9a-fA-F]{6}\b", path.read_text(encoding="utf-8")))
        assert n <= ALLOWED.get(rel, 0), (
            f"{rel}: {n} colour literals (allowed {ALLOWED.get(rel, 0)}): use kit/tokens.py"
        )


def test_themes_filters_and_roles():
    from astrowb.ui import theme

    assert (
        theme.colors("night") == theme.colors("dark") and theme.colors("light")["window"] == tokens.LIGHT["surface.0"]
    )
    assert tokens.filter_colour("V") == tokens.filter_colour("v") == "#3aa657"
    assert tokens.filter_colour("Rc") == tokens.FILTERS["R"] and tokens.filter_colour("SG") == tokens.FILTERS["g'"]
    assert tokens.filter_colour("Halpha") is None and tokens.role("comparison") == "#e8642c"
    assert tokens.contrast("#000000", "#ffffff") == pytest.approx(21.0)


def test_tabular_figures_with_either_tag_constructor(monkeypatch):
    """PySide 6.8 (the Linux ARM build) has no QFont.Tag(str) (the ARM installer stopped at start-up on it): the
    theme tries Tag.fromString, and goes on without tabular figures when there is neither."""
    pytest.importorskip("PySide6")
    from PySide6.QtGui import QFont

    from astrowb.ui import theme

    assert theme._tabular_figures(QFont())

    real = QFont.Tag

    class OldTag:
        def __init__(self, *args):
            if args:
                raise TypeError("PySide6.QtGui.QFont.Tag.__init__(str)")

        fromString = staticmethod(lambda s: real(s))  # noqa: N815

    monkeypatch.setattr(QFont, "Tag", OldTag)
    assert theme._tabular_figures(QFont())
    del OldTag.fromString  # PySide 6.8: no way to name a tag
    assert theme._tabular_figures(QFont()) is False
