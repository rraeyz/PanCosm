"""OBS-0: a safety rule that raises makes the observatory safe; it never leaves an unparked telescope unguarded."""

import warnings
from unittest import mock

import astropy.units as u
import pytest
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from fake_devices import FakeCamera, FakeDome, FakeMonitor, FakeMount

from astrowb.devices import observatory as obsmod
from astrowb.devices.observatory import Observatory, SafetyError
from astrowb.devices.safety import Rules

SITE = EarthLocation.from_geodetic(30.34 * u.deg, 36.82 * u.deg, 2500 * u.m)
NIGHT = Time("2026-11-15T22:00:00")
STALE = "interpolating from IERS_Auto using predictive values that are more than 30.0 days old"


@pytest.fixture(autouse=True)
def quiet():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


class Clock:
    t = 1000.0

    def __call__(self):
        return self.t


def make(**extra):
    clock = Clock()
    obs = Observatory(
        SITE, Rules(), clock=clock, now=lambda: NIGHT, mount=FakeMount(), dome=FakeDome(), camera=FakeCamera(), **extra
    )
    obs.test_clock = clock
    return obs


def unparked(obs):
    target = SkyCoord(AltAz(alt=60 * u.deg, az=120 * u.deg, obstime=NIGHT, location=SITE)).icrs
    obs.slew(target, poll_s=0)
    assert not obs.devices["mount"].AtPark


RULES = ("check_weather", "check_link", "check_sun")


@pytest.mark.parametrize("rule", RULES)
def test_a_rule_that_raises_parks_the_telescope_and_closes_the_dome(rule):
    obs = make(monitor=FakeMonitor())
    unparked(obs)
    obs.devices["monitor"].IsSafe = False  # a real reason as well: it must not be lost when another rule fails
    with mock.patch.object(obsmod, rule, side_effect=ValueError(STALE)):
        reasons = obs.supervise_once()
    assert obs.devices["mount"].AtPark and obs.devices["dome"].closed >= 1
    assert any(r.startswith("safety check") and "IERS" in r for r in reasons)
    if rule != "check_weather":
        assert "safety monitor reports unsafe" in reasons
    assert obs.last_check is not None


def test_the_stale_time_table_case_through_the_mount_position():
    obs = make()
    unparked(obs)
    with mock.patch.object(Observatory, "mount_position", side_effect=ValueError(STALE)):
        reasons = obs.supervise_once()
    assert obs.devices["mount"].AtPark
    assert reasons == [f"safety check sun and altitude failed: {STALE}"]


def test_a_crash_of_the_whole_check_is_made_safe_and_not_logged_every_cycle():
    obs = make()
    unparked(obs)
    with mock.patch.object(Observatory, "supervise_once", side_effect=RuntimeError("boom")):
        for _ in range(5):
            try:
                obs.supervise_once()
            except RuntimeError as e:
                obs._supervisor_failed(e)
            obs.test_clock.t += 5
    assert obs.devices["mount"].AtPark
    assert obs.reasons == ["safety check failed: boom"]
    assert sum("supervisor error" in line for line in obs.log) == 1


def test_a_slew_is_refused_when_the_rules_cannot_be_evaluated():
    obs = make()
    target = SkyCoord(AltAz(alt=60 * u.deg, az=120 * u.deg, obstime=NIGHT, location=SITE)).icrs
    with mock.patch.object(obsmod, "check_target", side_effect=ValueError(STALE)):
        with pytest.raises(SafetyError, match="the telescope was not moved"):
            obs.slew(target, poll_s=0)
    assert obs.devices["mount"].AtPark


def test_status_reports_how_old_the_last_check_is():
    from astrowb.devices.server import Controller

    obs = make()
    ctrl = Controller.__new__(Controller)
    ctrl.obs, ctrl.job = obs, None
    assert ctrl.status()["checked_s_ago"] is None
    obs.supervise_once()
    obs.test_clock.t += 30
    st = ctrl.status()
    assert st["checked_s_ago"] == 30 and st["check_interval_s"] == 5.0
