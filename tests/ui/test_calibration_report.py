"""UI-16.2: the Calibration window's Report and Log result tabs; synthetic result and task."""

from types import SimpleNamespace

import pytest

from astrowb.settings import Settings
from astrowb.ui import calibration_report as cr


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def test_report_text_lists_the_result_and_the_frames_left_out():
    assert "Calibrate" in cr.report_text(None)
    out = {"calibrated": ["a", "b"], "masters": ["m"], "arcs": ["x"], "dark_scales": [0.5, 1.25]}
    text = cr.report_text(out, [("f.fits", "saturated")])
    assert "2 images calibrated, 1 master" in text and "1 arc lamp" in text
    assert "0.500–1.250" in text and "f.fits: saturated" in text


def test_the_window_has_report_and_log_tabs_that_follow_a_run(window):
    win = window.open_area("calibrate")
    page = window.calibrate_page
    assert page.report_view.toPlainText().startswith("Calibrate")
    task = SimpleNamespace(progress=0.25, message="master bias")
    cr.start_log(page, task)
    cr.log_update(page, task)  # the same line twice is kept once
    task.progress, task.message = 0.75, "calibrating"
    cr.log_update(page, task)
    lines = page.log_view.toPlainText().splitlines()
    assert len(lines) == 2 and lines[0].endswith(" 25 %  master bias") and lines[1].endswith("calibrating")
    page.show_result({"calibrated": ["a"], "masters": []})
    assert "1 images calibrated" in page.report_view.toPlainText()
    win.close()
