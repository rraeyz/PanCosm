"""UI-16.2: the saved calibration report and the History result tab; synthetic data."""

import pytest

from astrowb.settings import Settings
from astrowb.ui import calibration_history as ch
from astrowb.ui import calibration_report as cr


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


class _Project:
    def runs(self, full=True):
        return [
            {"step": "calibration.run", "status": "done", "started": "2026-11-21T10:00:00", "error": None},
            {"step": "photometry.measure", "status": "done", "started": "2026-11-21T10:05:00", "error": None},
            {"step": "calibration.run", "status": "failed", "started": "2026-11-21T10:10:00", "error": "no bias"},
        ]


def test_history_lines_hold_calibration_runs_and_this_sessions_log_lines():
    log = (
        "2026-11-21 09:00:00 INFO astrowb.engine.tasks: task 1 calibration.run done after 1.0 s\n"
        "2026-11-21 11:00:00 INFO astrowb.engine.tasks: task 2 calibration.run running\n"
        "2026-11-21 11:00:01 INFO astrowb.engine.tasks: task 3 photometry.measure running\n"
    )
    lines = ch.history_lines(_Project(), log, "2026-11-21 10:30:00")
    assert len(lines) == 3 and "calibration.run failed: no bias" in lines[1] and "task 2" in lines[2]
    assert ch.history_lines(None, "", "") == []


def test_the_history_tab_is_hidden_until_it_has_lines_and_filters(window):
    window.open_area("calibrate")
    page = window.calibrate_page
    assert isinstance(page.history_dock, tuple) and not page.history_view.toPlainText()
    page._history_lines = ["a calibration.run done", "b calibration.run failed"]
    ch._show(page)
    assert not page.history_dock.isHidden() and page.history_view.focusPolicy().name == "NoFocus"
    page.history_filter.setText("failed")
    assert page.history_view.toPlainText() == "b calibration.run failed"


def test_the_report_is_saved_by_hand_and_beside_the_frames(window, tmp_path):
    window.open_area("calibrate")
    page = window.calibrate_page
    page.show_result({"calibrated": ["a"], "masters": []})
    out = tmp_path / "out"
    assert cr.save_beside_frames(page, str(out)) is None  # a folder that is not there is not made
    out.mkdir()
    (out / cr.FILE).write_text("old")
    path = cr.save_beside_frames(page, str(out))
    assert path == out / cr.FILE and "1 images calibrated" in path.read_text() and cr.FILE in page.review_status.text()
    assert cr.save_file(tmp_path / "x" / "r.txt", page) is False
    assert cr.save_file(tmp_path / "r.txt", page) and (tmp_path / "r.txt").exists()
    assert page.save_report_button.text().startswith("Save report")


def test_refresh_reads_app_log_and_the_project(window, tmp_path):
    window.open_area("calibrate")
    page = window.calibrate_page
    (tmp_path / "app.log").write_text("9999-01-01 00:00:00 INFO astrowb.engine.tasks: task 1 calibration.run done\n")
    ch.refresh(window, page)
    assert "task 1 calibration.run done" in page.history_view.toPlainText() and not page.history_dock.isHidden()
