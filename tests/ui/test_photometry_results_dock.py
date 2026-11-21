"""UI-16.1: the results dock holds results; the next-step buttons are in the Report stage and still work."""

import pytest

from astrowb.settings import Settings


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def test_next_buttons_are_in_the_report_stage_not_the_results_dock(window):
    window.show_workspace("photometry")
    page, win = window.photometry_page, window.area_windows["photometry"]
    report, dock = win.stage_panels["report"], win.docks["results"]
    for button in (page.go_period, page.go_model, page.export_button):
        assert report.isAncestorOf(button)
        assert not dock.isAncestorOf(button)


def test_period_search_button_still_emits(window, qtbot):
    window.show_workspace("photometry")
    page = window.photometry_page
    with qtbot.waitSignal(page.next_requested) as got:
        page.go_period.click()
    assert got.args == ["timeseries", ""]
