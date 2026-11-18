"""Planning reads the profile site's horizon and time zone (ARC-16)."""

import pytest

from astrowb.core import profiles
from astrowb.core.profiles import zone_offset
from astrowb.ui.plan_page import PlanPage


def _zones():
    from zoneinfo import ZoneInfo

    try:
        ZoneInfo("Europe/Istanbul")
    except Exception:  # Windows without the tzdata package has no zone database
        return False
    return True


needs_zones = pytest.mark.skipif(not _zones(), reason="no IANA time zone database on this system")

JD = 2461000.5  # northern winter


@needs_zones
def test_zone_offset_and_bad_names():
    assert zone_offset("Europe/Istanbul", JD) == 3.0
    assert zone_offset("America/New_York", JD) == -5.0
    for bad in ("", "Not/AZone", "../x"):
        assert zone_offset(bad, JD) is None


@pytest.fixture
def page_for(qtbot, tmp_path_factory):
    def make(**site):
        from astrowb.settings import Settings

        s = Settings(tmp_path_factory.mktemp("cfg"))
        profiles.update(s, "site", **site)
        page = PlanPage(s)
        qtbot.addWidget(page)
        return page

    return make


def test_horizon_sets_lowest_altitude(page_for):
    assert page_for().min_alt.value() == 20.0
    assert page_for(horizon=35.0).min_alt.value() == 35.0


@needs_zones
def test_time_zone_sets_local_offset(page_for):
    page = page_for(time_zone="America/New_York")
    assert page.local_offset(JD) == -5.0
    page.utc_offset.setValue(2.0)  # the typed offset still wins
    assert page.local_offset(JD) == 2.0


def test_bad_time_zone_falls_back(page_for):
    bad, none = page_for(time_zone="Nowhere/Land"), page_for()
    assert bad.local_offset(JD) == none.local_offset(JD)


def test_horizon_changes_which_targets_are_up(page_for):
    import numpy as np

    from astrowb.planning.schedule import schedule

    jd = 2461000.0 + np.linspace(0, 0.5, 50)
    alt = np.full(50, 25.0)  # a target that stays at 25 deg all night
    night = {
        "jd": jd.tolist(),
        "dusk": jd[0],
        "dawn": jd[-1],
        "targets": [{"name": "A", "events": [], "alt": alt.tolist()}],
    }
    target = [{"name": "A", "ra": 0.0, "dec": 0.0}]
    low, high = page_for().min_alt.value(), page_for(horizon=35.0).min_alt.value()
    assert schedule(night, target, min_alt=low) and not schedule(night, target, min_alt=high)
