"""UI-16.12: Schedule."""

from datetime import datetime

from PySide6.QtCore import QTime

from astrowb.settings import Settings
from astrowb.ui.automation_page import AutomationPage
from astrowb.ui.automation_schedule import cancel_schedule, next_delay_ms, schedule_at


def _page(qtbot, tmp_path):
    page = AutomationPage(Settings(tmp_path))
    qtbot.addWidget(page)
    page.set_automation({"name": "t", "steps": [{"step": "fits.save_as"}]})
    return page


def test_next_delay_is_today_or_tomorrow():
    now = datetime(2026, 11, 21, 22, 0, 0)
    assert next_delay_ms(QTime(22, 30), now) == 30 * 60 * 1000
    assert next_delay_ms(QTime(21, 0), now) == 23 * 3600 * 1000


def test_schedule_runs_and_cancel_stops(qtbot, tmp_path):
    page = _page(qtbot, tmp_path)
    runs = []
    page._run = lambda row=0: runs.append(1)
    schedule_at(page, QTime(22, 30), delay_ms=20)
    assert not page.schedule_row.isHidden() and "22:30" in page.schedule_label.text()
    qtbot.waitUntil(lambda: bool(runs), timeout=2000)
    assert page.schedule_row.isHidden()
    schedule_at(page, QTime(22, 30), delay_ms=20)
    cancel_schedule(page)
    qtbot.wait(100)
    assert runs == [1] and page.schedule_timer is None
