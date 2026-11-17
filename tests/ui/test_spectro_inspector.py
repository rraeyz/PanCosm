"""UI-16.3: the job switch is a Segmented, and the inspector shows the selected arc line and its fit."""

import pytest

from astrowb.settings import Settings
from astrowb.ui.spectro_inspector import line_rows


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def _fill(tab, rows):
    tab.guesses.setRowCount(len(rows))
    from PySide6.QtWidgets import QTableWidgetItem

    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            tab.guesses.setItem(r, c, QTableWidgetItem(text))


def test_the_job_switch_is_a_segmented_that_follows_the_tabs(window):
    win = window.open_area("spectroscopy")
    page, switch = window.spectro_page, win.job_switch
    assert list(switch.buttons) == [str(i) for i in range(page.tabs.count())]
    switch.setValue("1")
    assert page.tabs.currentWidget() is page.echelle_tab
    page.tabs.setCurrentWidget(page.tools_tab)
    assert switch.value() == "5"
    win.close()


def test_line_rows_hold_the_line_and_the_fit(window):
    tab = window.spectro_page.reduce_tab
    _fill(tab, [["100.00", "5000.0"], ["200.00", ""]])
    assert dict((n, v) for n, v, _ in line_rows(tab, 1))["Pixel"] == 200.0
    assert dict((n, v) for n, v, _ in line_rows(tab, 1))["Wavelength"] is None
    tab.result = {"solution": {"lines": [[100.0, 5000.0, 0.0123]], "n_lines": 5, "degree": 2, "rms": 0.04}}
    rows = {n: (v, u) for n, v, u in line_rows(tab, 0)}
    assert rows["Residual"] == (12.3, "mÅ") and rows["Left out"][0] == "no"
    assert rows["Lines in the fit"][0] == 5 and rows["rms"] == (0.04, "Å")
    tab.excluded_lines.append(100.0)
    assert {n: v for n, v, _ in line_rows(tab, 0)}["Left out"] == "yes"


def test_the_inspector_follows_the_selected_row_and_the_job(window):
    win = window.open_area("spectroscopy")
    page, dock = window.spectro_page, win.docks["inspector"]
    assert dock.isHidden()
    _fill(page.echelle_tab, [["30", "10.0", "6000.0"]])
    page.tabs.setCurrentWidget(page.echelle_tab)
    page.echelle_tab.guesses.setCurrentCell(0, 1)
    assert not dock.isHidden()
    assert [n for n, *_ in win.line_inspector.rows][:2] == ["Order", "Pixel"]
    page.tabs.setCurrentWidget(page.velocity_tab)
    assert dock.isHidden()
    win.close()
