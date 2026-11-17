"""UI-16.3: the Spectrum tools' lines table shows the chosen measured line and its fit in the inspector."""

import numpy as np
import pytest

from astrowb.settings import Settings
from astrowb.ui.spectro_tools_inspector import tool_rows, window_data


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def _measured():
    from astrowb.spectroscopy.analysis import measure_line

    w = np.linspace(6500, 6600, 400)
    f = 1 - 0.5 * np.exp(-0.5 * ((w - 6550) / 2.0) ** 2) + np.random.default_rng(1).normal(0, 0.005, w.size)
    return w, f, measure_line(w, f, 6530, 6570, "gauss")


def test_tool_rows_hold_only_what_the_result_holds():
    w, f, m = _measured()
    rows = {n: (v, u) for n, v, u in tool_rows("a.fits", m)}
    assert rows["Centre"][0] == m["centre"] and rows["σ Centre"][0] == m["centre_err"]
    assert "V/R" not in rows and rows["Profile"][0] == "gauss"
    ww, ff = window_data(w, f, m)
    assert len(ww) == len(ff) and min(ww) >= m["lo"] and max(ww) <= m["hi"]


def test_the_inspector_shows_the_chosen_measured_line(window):
    win = window.open_area("spectroscopy")
    page, dock = window.spectro_page, win.docks["inspector"]
    tools = page.tools_tab
    assert dock.isHidden()
    w, f, m = _measured()
    page.tabs.setCurrentWidget(tools)
    tools._add_row("a.fits", m, (w, f))
    tools.table.row_chosen.emit(0)
    assert not dock.isHidden()
    assert [n for n, *_ in win.line_inspector.rows][:2] == ["File / date", "Centre"]
    assert not win.line_inspector.tool_plot_box.isHidden()
    page.tabs.setCurrentWidget(page.velocity_tab)
    assert dock.isHidden()
    win.close()
