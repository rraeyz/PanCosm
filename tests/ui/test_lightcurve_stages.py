"""UI-16.4: the Fold and Report stages and the peak table in the Light curves window's inspector."""

import numpy as np
import pytest

from astrowb.settings import Settings
from astrowb.ui.lightcurve_fold import peak_table


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def _result():
    periods = np.geomspace(0.1, 5, 400)
    power = np.exp(-(((np.log(periods) - np.log(0.7)) / 0.02) ** 2)) + 0.5 * np.exp(
        -(((np.log(periods) - np.log(1.4)) / 0.02) ** 2)
    )
    return {"best": 0.7, "periods": periods.tolist(), "power": power.tolist()}


def test_peak_table_lists_local_maxima_highest_first():
    table = peak_table(_result())
    assert table.colnames == ["period", "power", "fap"]  # FAP is "—" without the step peak_faps
    assert abs(table["period"][0] - 0.7) < 0.03 and abs(table["period"][1] - 1.4) < 0.06
    assert table["power"][0] >= table["power"][1]
    assert len(peak_table({"periods": [], "power": []})) == 0


def test_fold_and_report_stages_and_the_peak_table(window):
    win = window.open_area("timeseries")
    page = window.lightcurve_page.period_page
    assert list(win.stage_panels) == ["data", "clean", "search", "fold", "frequencies", "variables", "report"]
    assert win.stage_panels["fold"].isAncestorOf(page.phase_bins)
    assert not win.stage_panels["search"].isAncestorOf(page.phase_bins)
    assert win.stage_panels["report"].isAncestorOf(page.save_button)
    assert not win.stage_panels["data"].isAncestorOf(page.save_button)
    assert not win.docks["inspector"].isVisibleTo(win)  # until a search has run
    t = np.linspace(0, 10, 300)
    page.set_light_curve(t.tolist(), (1 + 0.1 * np.sin(2 * np.pi * t / 0.7)).tolist(), "synthetic")
    page.show_result(_result())
    assert win.docks["inspector"].isVisibleTo(win)
    view = win.docks["inspector"].widget()
    assert view.model.rowCount() >= 2
    view.row_chosen.emit(1)  # a row folds at that peak
    assert abs(page.best - 1.4) < 0.06
    win.show_stage("report")
    assert window.lightcurve_page.currentIndex() == 0
    win.close()


def test_points_left_out_are_gone_from_every_plot_and_the_periodogram_is_marked_stale(qtbot):
    """UI-16.4: one list of points in use feeds the time and the folded plot; the periodogram is marked until a new
    search; Undo edits restores the points."""
    from astrowb.ui.period_page import PeriodPage

    page = PeriodPage()
    qtbot.addWidget(page)
    t = np.linspace(0, 10, 60)
    page.set_light_curve(t, 1 + 0.01 * np.sin(t), "test")
    page.delete_points([1, 2])  # in the time plot
    assert len(page.time) == 58 and t[1] not in page.time
    periods = np.linspace(1, 5, 20)
    out = {"best": 2.0, "periods": periods, "power": np.ones(20)}
    page.show_result(out)
    assert page._period_label() == "Period (d)"
    page.delete_points([0])  # in the folded plot (same path)
    assert len(page.time) == 57 and t[0] not in page.time
    assert "out of date" in page._period_label()
    page.show_result(out)  # a new search uses only the rest
    assert "out of date" not in page._period_label()
    page.delete_points([5])
    page.undo_button.click()
    assert len(page.time) == 60
