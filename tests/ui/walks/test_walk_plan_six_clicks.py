"""PLN-W accept: from an empty Planning window, "What can I observe tonight?" → three results → chart → schedule →
Send to Observing. The finder is given the recorded Exoplanet Archive sample, never the network. Today the flow
takes 11 clicks (the six-click goal is a strict expected failure until the finder asks, adds and plots by itself)."""

from pathlib import Path

import pytest
from PySide6.QtCore import QDate, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "exoplanet_archive_sample.csv"


def _flow(walk, monkeypatch):
    from astrowb.ui import plan_finder

    real = plan_finder.FinderDialog
    recorded = lambda url: SAMPLE.read_text(encoding="utf-8")  # noqa: E731
    monkeypatch.setattr(plan_finder, "FinderDialog", lambda page, fetch=None: real(page, recorded))
    h = walk("en")
    h.main.settings.set("areas.show_experimental", True)  # Send to Observing is shown only then
    h.area("plan")
    page = h.page
    page.lat.setValue(39.84)  # the site is not part of the six clicks
    page.lon.setValue(32.78)
    page.min_alt.setValue(30)
    page.date.setDate(QDate(2026, 11, 14))
    h.menu("What can I observe tonight?…")
    dlg = next(w for w in QApplication.topLevelWidgets() if isinstance(w, real) and w.isVisible())
    page.finder = dlg  # h.find reaches it through the page
    h.click("finder.fetch_button")
    h.wait(lambda: len(dlg.events) >= 3)
    table = dlg.view.table
    for row in range(3):
        pos = table.visualItemRect(table.item(row, 0)).center()
        h._act(f"pick result {row}", lambda pos=pos: QTest.mouseClick(table.viewport(), Qt.LeftButton, pos=pos), 2.0)
        h.click("finder.add_button")
    h.click("plan_button")
    h.wait(lambda: page.result is not None)
    h.click("schedule_button")
    sent = []
    page.schedule_requested.connect(sent.append)
    h.click("send_button")
    h.check()
    assert len(page.targets()) == 3 and page.blocks and sent == [page.blocks]
    return len(h.timings)


def test_tonights_planets_to_observing(walk, monkeypatch):
    assert _flow(walk, monkeypatch) == 11


@pytest.mark.xfail(strict=True, reason="PLN-W: Fetch, pick + Add and Plan the night are still separate clicks")
def test_in_six_clicks(walk, monkeypatch):
    assert _flow(walk, monkeypatch) <= 6


def test_no_site_says_so_and_opens_the_profile(walk):
    h = walk("en")
    h.area("plan")
    page = h.page
    h.wait(lambda: page.almanac.text().startswith("No site saved yet"))
    assert page.site_button.isVisibleTo(page)
    h.click("site_button")
    from astrowb.ui.settings_window import SettingsWindow

    box = next(w for w in QApplication.topLevelWidgets() if isinstance(w, SettingsWindow))
    assert box.categories.currentRow() == box.profiles_category
