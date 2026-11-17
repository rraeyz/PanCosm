"""UI-16.13: the inspector of the Remote sensing window: band values and spectrum of the clicked pixel."""

import sys
from pathlib import Path

import pytest

from astrowb.settings import Settings

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_remotesensing import scene  # noqa: E402


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path / "cfg"))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def test_a_click_fills_the_pixel_inspector(window, tmp_path):
    win = window.open_area("remotesensing")
    page = window.rs_page
    page.open(str(scene(tmp_path)[0]))
    dock = win.docks["inspector"]
    assert win.pixel_inspector.rows == [] and not dock.isVisible()
    r = page.raster
    page.viewer.clicked.emit(10.0, float(r.shape[0] - 1 - 5))  # image pixel (10, 5)
    rows = {name: value for name, value, _ in win.pixel_inspector.rows}
    assert dock.isVisible() and rows["x"] == 10 and rows["y"] == 5
    assert [n for n in r.names if n in rows] == r.names
    assert rows[r.names[3]] == pytest.approx(float(r.bands[3, 5, 10]))
    assert "Latitude" in rows
    page.viewer.clicked.emit(1e6, 1e6)  # outside: unchanged
    assert {n: v for n, v, _ in win.pixel_inspector.rows}["x"] == 10
