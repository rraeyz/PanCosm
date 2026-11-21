"""UI-16.11: the Astrometry inspector shows the chosen measurement row and stays hidden until then."""

import pytest

from astrowb.settings import Settings


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def rows(n=4):
    return [
        {"file": f"/d/a{i}.fits", "time": f"2026-11-15T21:{10 + i}:00.000", "x": 20.0 + i, "y": 30.0,
         "ra": 150.0 + i * 1e-3, "dec": 20.0, "ast_cat": "Gaia3", "resid": 0.5 * i}
        for i in range(n)
    ]  # fmt: skip


def test_the_inspector_follows_the_chosen_position(window):
    win = window.open_area("astrometry")
    page = window.astrometry_page
    dock = win.docks["inspector"]
    page.show_positions(rows())
    assert not dock.isVisible()
    page.table.setCurrentCell(2, 0)
    shown = {name: value for name, value, *_ in win.position_inspector.rows}
    assert dock.isVisible() and shown["Frame"] == "a2.fits" and shown["Residual"] == 1.0
    assert shown["rms"] == (sum((0.5 * i) ** 2 for i in range(4)) / 4) ** 0.5 and shown["Catalogue"] == "Gaia3"
    win.close()
