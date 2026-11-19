"""Owner decision 2026-11-27: the unfinished areas hide behind areas.show_experimental (entry points only)."""

import pytest

from astrowb.settings import Settings
from astrowb.ui import start_page

HIDDEN = ("Spectroscopy", "Remote sensing", "Astrometry", "Observing", "Automation")


def _window(qtbot, tmp_path, monkeypatch, on):
    from astrowb.ui.main_window import MainWindow

    monkeypatch.setattr(
        start_page, "EXPERIMENTAL", {"spectroscopy", "remotesensing", "astrometry", "observe", "automation"}
    )
    settings = Settings(tmp_path)
    settings.set("areas.show_experimental", on)
    win = MainWindow(settings)
    qtbot.addWidget(win)
    return win


def _lists(win):
    win._fill_window_menu()
    sub = next(a.menu() for a in win.window_menu.actions() if a.menu() is not None)
    from astrowb.ui import start_search

    return (
        [b.label.text() for b in win.start_page.blocks],
        [a.text() for a in sub.actions()],
        [text for text, _ in start_search.commands(win)],
    )


@pytest.mark.parametrize("on", [False, True])
def test_hidden_areas_are_listed_only_when_shown(qtbot, tmp_path, monkeypatch, on):
    win = _window(qtbot, tmp_path, monkeypatch, on)
    try:
        blocks, menu, palette = _lists(win)
        for name in HIDDEN:
            assert any(f"<b>{name}</b>" in b for b in blocks) == on
            assert (name in menu) == on
            assert any(t == f"Areas › {name}" for t in palette) == on
        assert any("Planning" in b for b in blocks)
        assert "Asteroid and comet astrometry…" in " ".join(
            a.text().replace("&", "") for a in win.image_bar_menu.actions()
        )
        win.open_area("spectroscopy")  # hiding is only about entry points: opening never fails
    finally:
        win.engine.shutdown()
