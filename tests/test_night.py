"""PLN-1: the almanac of a night at four sites, the horizon profile in every observability answer, a month view."""

import numpy as np
import pytest

from astrowb.engine.steps import execute
from astrowb.planning import night
from astrowb.planning.visibility import Site

TUG = Site("TUG", 36.8242, 30.3356, 2500.0)


class Ctx:
    def progress(self, *a):
        pass

    def check(self):
        pass


def test_almanac_at_the_equator_and_mid_latitude():
    eq = night.summary(Site("equator", 0.0, 0.0), "2026-03-20")
    length = (eq["sun_up"] + 24 - eq["sun_down"]) if eq["sun_up"] < eq["sun_down"] else eq["sun_up"] - eq["sun_down"]
    assert length == pytest.approx(24 - 12 - 2 * 3.5 / 60, abs=0.06)  # 12 h of day + ~7 min of refraction and disc
    s = night.summary(TUG, "2026-11-13")
    order = [s[k] for k in ("sun_down", "civil_down", "nautical_down", "astronomical_down")]
    assert order == sorted(order) and s["astronomical_up"] < s["nautical_up"] < s["civil_up"] < s["sun_up"]
    assert 14.7 < s["sun_down"] < 14.95  # the chart's 14:46 (Sun's centre at 0°), a few minutes later at −0.833°
    assert 9 < s["dark_hours"] < 12 and 0 <= s["moon_illumination"] <= 1
    assert all(0 <= s[k] < 24 for k in ("lst_down", "lst_midnight", "lst_up"))


def test_polar_summer_and_winter():
    summer = night.summary(Site("68N", 68.0, 20.0), "2026-06-21")
    assert summer["sun_down"] is None and summer["dark_hours"] == 0
    winter = night.summary(Site("68N", 68.0, 20.0), "2026-12-21")
    assert winter["sun_up"] is None and winter["sun_down"] is None and winter["dark_hours"] > 12


def test_horizon_profile_parsed_and_used():
    text = "# my roof\naz alt\n0 10\n90, 45\n180;10\n270\t10\n"
    horizon = night.parse_horizon(text)
    assert horizon == [(0.0, 10.0), (90.0, 45.0), (180.0, 10.0), (270.0, 10.0)]
    assert night.limit(horizon, [90.0, 45.0, 315.0], 20.0).tolist() == [45.0, 27.5, 20.0]
    with pytest.raises(ValueError):
        night.parse_horizon("nothing here")
    site = {
        "name": "TUG",
        "lat": 36.8242,
        "lon": 30.3356,
        "height": 2500.0,
        "horizon": [(0, 5), (60, 85), (120, 85), (180, 5)],
    }  # fmt: skip — a wall to the east
    out = execute("planning.night", {"site": site, "date": "2026-11-13", "targets": [{"name": "Saturn", "ra": 0,
                  "dec": 0}]}, {"min_alt": 20.0, "step_min": 10.0}, Ctx())["night"]  # fmt: skip
    t = out["targets"][0]
    az, alt, floor = (np.asarray(t[k]) for k in ("az", "alt", "limit"))
    east = (az > 70) & (az < 110) & (alt > 20)
    assert east.any() and np.all(alt[east] < floor[east])  # above 20° but behind the wall: not observable


def test_a_month_of_nights():
    m = night.month(TUG, "2026-11-01", 8)
    assert len(m) == 8 and m[0]["date"] == "2026-11-01" and all(9 < n["dark_hours"] < 12 for n in m)


def test_the_plan_page_loads_a_horizon_and_sends_it(qapp, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.plan_page import PlanPage

    page = PlanPage(Settings(tmp_path))
    (tmp_path / "h.txt").write_text("0 10\n90 40\n180 10\n270 10\n", encoding="utf-8")
    page.load_horizon(str(tmp_path / "h.txt"))
    assert "4 points" in page.horizon_button.text()
    sent = []
    page.plan_requested.connect(lambda site, *rest: sent.append(site))
    page.add_target({"name": "Vega", "ra": 279.23, "dec": 38.78, "source": "typed"})
    page._plan()
    assert sent and sent[0]["horizon"][1] == (90.0, 40.0)
    assert PlanPage(Settings(tmp_path)).horizon[1] == (90.0, 40.0)  # kept in the settings
    (tmp_path / "e.txt").write_text("\n", encoding="utf-8")
    page.load_horizon(str(tmp_path / "e.txt"))
    assert page.horizon == [] and "none" in page.horizon_button.text()
