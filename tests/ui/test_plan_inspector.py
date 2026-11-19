"""UI-16.8: the Planning inspector shows the chosen target and tonight's events, or an empty-state line."""

import pytest
from PySide6.QtCore import QDate

from astrowb.settings import Settings


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def test_the_inspector_follows_the_chosen_target(window, qtbot):
    win = window.open_area("plan")
    page = window.plan_page
    panel = win.target_inspector
    assert "Select a target to see its details" in panel.copy_text()
    assert not win.docks["inspector"].isVisible()
    page.date.setDate(QDate(2026, 11, 15))
    page.lat.setValue(36.82)
    page.lon.setValue(30.34)
    page.add_target({"name": "T", "ra": 31.04, "dec": 46.688, "source": "typed"})
    page.table.item(0, 3).setText("2461000.40")
    page.table.item(0, 4).setText("0.35")
    page.table.setCurrentCell(0, 0)
    assert win.docks["inspector"].isVisible()
    text = panel.copy_text()
    assert "02 04 09.6" in text and "46 41 17" in text and "plan the night" in text
    page.plan_button.click()
    qtbot.waitUntil(lambda: page.result is not None, timeout=60000)
    text = panel.copy_text()
    assert "Minimum I" in text or "Minimum II" in text
    assert "Above the limit" in text and "Moon distance at the highest" in text
    page.table.setCurrentCell(-1, -1)
    assert "Select a target to see its details" in panel.copy_text()
