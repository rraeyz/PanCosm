"""UI-16.3: the instrument profile also in the toolbar; Velocities, Telluric and Spectrum tools in several stages."""

import pytest
from PySide6.QtWidgets import QPushButton

from astrowb.settings import Settings


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def test_the_toolbar_profile_combo_and_the_overview_one_agree(window):
    win = window.open_area("spectroscopy")
    page, combo = window.spectro_page, win.profile_combo
    page.save_profile("A")
    page.save_profile("B")
    assert [combo.itemText(i) for i in range(combo.count())] == ["A", "B"]
    assert combo.currentText() == page.profile.currentText() == "B"
    combo.setCurrentIndex(0)
    combo.activated.emit(0)  # a choice in the toolbar moves the overview's list
    assert page.profile.currentText() == "A"
    page.profile.setCurrentIndex(1)  # and the other way
    assert combo.currentText() == "B"
    win.close()


@pytest.mark.parametrize("job", ["telluric", "velocity", "tools"])
def test_split_jobs_have_stages_and_keep_every_widget(window, job):
    win = window.open_area("spectroscopy")
    page = window.spectro_page
    wanted = {
        "telluric": {"Correct and save"},
        "velocity": {"Measure radial velocities", "Fit orbit"},
        "tools": {"Open spectrum…", "Combine exposures…"},
    }
    keys = [k for k in page.stage_boxes if k.startswith(job + "_")]
    assert len(keys) >= 2 and job not in page.stage_boxes
    assert all(k in win.rail.buttons for k in keys)
    inside = {w for k in keys for w in page.stage_boxes[k].findChildren(QPushButton)}
    texts = {b.text().replace("\n", " ") for b in inside}
    assert wanted[job] <= texts
    win.close()
