import pytest

from astrowb.settings import Settings


@pytest.fixture
def setup(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    window = MainWindow(Settings(tmp_path))
    qtbot.addWidget(window)
    win = window.open_area("observe")
    yield win, window.observe_page
    win.close()
    window.engine.shutdown()


STATUS = {
    "devices": {"mount": 1.0, "camera": 1.0, "focuser": 1.0, "filterwheel": 1.0},
    "camera": {"CCDTemperature": -10.04, "CoolerOn": True},
    "focuser": {"Position": 12034, "IsMoving": True},
    "filterwheel": {"Position": 1, "Names": ["B", "V"]},
    "mount": {"parked": False, "tracking": True},
}


def test_chips_show_the_polled_state_and_click_opens_the_stage(setup):
    win, page = setup
    chips = win.observe_chips
    chips.update(STATUS)
    assert set(chips.chips) == {"mount", "camera", "focuser", "filterwheel"}
    assert chips.chips["camera"].text() == "Camera -10.0 °C"
    assert chips.chips["filterwheel"].text() == "Filter wheel V"
    assert chips.chips["mount"].text() == "Mount tracking"
    assert chips.chips["focuser"].styleSheet()  # busy: coloured
    assert not chips.chips["camera"].styleSheet()
    chips.update(STATUS | {"mount": {"error": "x"}})
    assert chips.chips["mount"].styleSheet()  # lost
    chips.chips["focuser"].click()
    assert win.stage_panels[win.current_stage()].isAncestorOf(page.focus_pos)
    assert ("Position", 12034, "") in chips.inspector.rows


def test_inspector_shows_the_selected_exposure_row(setup):
    win, page = setup
    if not page.exposures.rowCount():
        page.add_exposure_row()
    page.exposures.setCurrentCell(0, 1)
    chips = win.observe_chips
    chips.show_exposure()
    names = [r[0] for r in chips.inspector.rows]
    assert names == ["Kind", "Filter", "Exposure", "Count", "Binning"]
