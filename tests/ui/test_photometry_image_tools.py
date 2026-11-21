"""UI-16.1: the Images window's Star, Area and Line tools on the Photometry window's image."""

import numpy as np
import pytest

from astrowb.settings import Settings

SIGMA, AMP, SKY = 1.7, 5000.0, 100.0


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def _shown(window):
    page = window.photometry_page
    window.show_workspace("photometry")
    yy, xx = np.mgrid[0:100, 0:120]
    data = SKY + AMP * np.exp(-((xx - 50.0) ** 2 + (yy - 40.0) ** 2) / (2 * SIGMA**2))
    page.viewer.set_image(data.astype(np.float32))
    page.images = ["x.fits"]
    return page, window.area_windows["photometry"], page.image_tools


def test_star_tool_measures_fwhm_and_counts(window):
    page, win, tools = _shown(window)
    tools.set_tool("aperture")
    s = tools.measure_star(50.0, 40.0)
    assert s["fwhm"] == pytest.approx(2.3548 * SIGMA, rel=0.08)
    assert s["net_counts"] == pytest.approx(2 * np.pi * SIGMA**2 * AMP, rel=0.1)
    assert s["background"] == pytest.approx(SKY, abs=1)
    assert not win.docks["measure"].isHidden()  # its numbers came up


def test_a_click_with_the_star_tool_measures_and_does_not_mark(window):
    page, win, tools = _shown(window)
    tools.set_tool("aperture")
    page.viewer.clicked.emit(50.0, 40.0)
    assert page.target is None and not page.comps
    assert tools._graph_data is not None  # the profile was drawn


def test_default_click_still_picks_a_star(window):
    page, win, tools = _shown(window)
    assert page.viewer.tool == "pan"
    page.viewer.clicked.emit(50.0, 40.0)
    assert page.target is not None and abs(page.target[0] - 50.0) < 1 and abs(page.target[1] - 40.0) < 1


def test_area_and_line_tools(window):
    page, win, tools = _shown(window)
    tools.set_tool("area")
    page.viewer.region_selected.emit(40.0, 30.0, 60.0, 50.0)
    a = tools._area_box
    assert a["pixels"] == 21 * 21 and a["max"] == pytest.approx(SKY + AMP, rel=0.01)
    tools.set_tool("line")
    page.viewer.line_selected.emit(30.0, 40.0, 70.0, 40.0)
    assert page.target is None
    assert tools._graph_data[2].max() == pytest.approx(SKY + AMP, rel=0.01)
