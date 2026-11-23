"""CAL-W extra accept: the practice night in the Calibration window: the raw folder dropped on the window -> the
plan (each light group's bias, dark and flat) is shown without a Scan press -> one click calibrates -> Review shows
the light raw and calibrated; three actions at most, the drop counted."""

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QComboBox, QToolBar

from astrowb import sampledata

ACTIONS = ("click ", "choose ", "menu ", "drop ")


@pytest.mark.slow
@pytest.mark.parametrize("lang", ["en", "tr"])
def test_practice_night_dropped_planned_calibrated_and_reviewed_in_three_actions(walk, tmp_path, lang):
    sampledata.make(tmp_path / "night", n_lights=24)
    h = walk(lang)
    h.main.open_project(tmp_path / "p.astroproj")
    win = h.area("calibrate")
    page = h.main.calibrate_page
    h.drop([tmp_path / "night" / "raw"])  # 1: scanned on the drop
    h.wait(lambda: page.plan_table.table.rowCount() > 0 and page.run_button.isEnabled())
    plan = page.plan_table.table
    for r in range(plan.rowCount()):
        boxes = [plan.cellWidget(r, c) for c in (3, 4, 5)]  # bias, dark, flat
        assert all(isinstance(b, QComboBox) and b.currentData() == "auto" for b in boxes)
        assert not plan.item(r, 6).text(), plan.item(r, 6).text()  # nothing missing
    # 2: the toolbar's Calibrate, from any stage (on the toolbar: "Kalibrasyon" also names the area in a menu in tr)
    text = QCoreApplication.translate("MainWindow", "Calibrate")
    tool = next(t.widgetForAction(a) for t in win.findChildren(QToolBar) for a in t.actions() if a.text() == text)
    tool.setObjectName("calibrate_tool")
    h.click("calibrate_tool")
    h.wait(lambda: page.photometry_button.isEnabled())
    assert win.current_stage() == "review", h.timings
    ba = page.before_after
    assert ba.pair is not None and ba.isVisible() and ba.calibrated_button.isEnabled()
    h.check()
    assert sum(t[0].startswith(ACTIONS) for t in h.timings) <= 3, h.timings
