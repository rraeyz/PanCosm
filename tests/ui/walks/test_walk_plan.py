"""VAL-8: the Plan window as a user goes through it (the guided task plan-eclipses.toml without the network): the
site by its name, a target by its coordinates, its ephemeris typed into the table, Plan the night."""

import pytest
from PySide6.QtCore import QDate


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_plan_the_eclipses_of_a_night(walk, lang):
    h = walk(lang)
    h.area("plan")
    page = h.page
    page.date.setDate(QDate(2026, 11, 15))  # a fixed night with the target high (the date field is the calendar's)
    h.type("site_name", "TUG")
    assert page.lat.value() == pytest.approx(36.82, abs=0.05)
    h.type("target_input", "02:04:10 +46:41:16")
    h.wait(lambda: page.table.rowCount() == 1)
    t0, period = 2461000.40, 0.35  # an eclipse every 8.4 h: one at least in the night
    h.cell("table", 0, 3, str(t0))
    h.cell("table", 0, 4, str(period))
    h.click("plan_button")
    h.wait(lambda: getattr(page, "result", None) is not None)
    h.check()
    events = page.result["targets"][0]["events"]
    assert events, "no eclipse listed in a 13-hour November night at TUG"
    for e in events:
        cycles = 2 * (e["mid"] - t0) / period  # primary and secondary minima
        # the ephemeris is in BJD, the night's times in UTC: they differ by the light's way to the Sun (≤ 8.3 min)
        assert abs(cycles - round(cycles)) * period / 2 < 9 / 1440
