"""PLN-12: a recorded sample of the Gaia Science Alerts list parses into targets; the ones above the altitude limit
in tonight's dark hours are kept; nothing is fetched unless asked (a fake fetch here)."""

from pathlib import Path

from astrowb.planning.visibility import Site
from astrowb.services import feeds_gaia

SAMPLE = (Path(__file__).parent / "data" / "gaia_alerts_sample.csv").read_text(encoding="utf-8")


def test_gaia_alerts_parse_and_tonight():  # conftest gives every test its own settings and cache folder
    rows = feeds_gaia.parse(SAMPLE)
    assert len(rows) >= 30 and rows[0]["name"].startswith("Gaia")
    assert all(0 <= r["ra"] < 360 and -90 <= r["dec"] <= 90 for r in rows)
    asked = []
    got = feeds_gaia.alerts(fetch=lambda url: asked.append(url) or SAMPLE)
    assert asked == [feeds_gaia.URL] and len(got) == len(rows)
    site = Site("Ankara", 39.84, 32.78, 1250.0)
    tonight = feeds_gaia.observable(rows, site, "2026-11-14", min_alt=30)
    assert tonight and all(r["max_alt"] >= 30 for r in tonight)
    assert all(r["dec"] > 39.84 - 90 + 30 for r in tonight)  # a target must reach 30° at this latitude
    assert len(tonight) < len(rows)  # far-southern alerts never rise high enough here


def test_alerts_dialog_adds_a_target(qtbot):
    from PySide6.QtCore import QDate

    from astrowb.settings import Settings
    from astrowb.ui.plan_page import PlanPage

    page = PlanPage(Settings())
    qtbot.addWidget(page)
    page.lat.setValue(39.84)
    page.lon.setValue(32.78)
    page.date.setDate(QDate(2026, 11, 14))
    asked = []
    dlg = page.alerts_dialog(fetch=lambda url: asked.append(url) or SAMPLE)
    assert asked == []  # nothing fetched until Fetch is pressed
    dlg.fetch_button.click()
    qtbot.waitUntil(lambda: bool(dlg.rows), timeout=20000)
    assert asked and dlg.view.table.rowCount() == len(dlg.rows)
    dlg.chosen = [0]
    before = page.table.rowCount()
    dlg.add_chosen()
    assert page.table.rowCount() == before + 1 and page.table.item(before, 0).text() == dlg.rows[0]["name"]
