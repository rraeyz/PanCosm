import warnings

import astropy.units as u
import pytest
from astropy.coordinates import AltAz, EarthLocation, SkyCoord, get_body
from astropy.time import Time

from astrowb.devices.safety import Rules, check_link, check_target, check_weather

SITE = EarthLocation.from_geodetic(30.34 * u.deg, 36.82 * u.deg, 2500 * u.m)
NIGHT = Time("2026-11-15T22:00:00")
DAY = Time("2026-11-15T10:00:00")


@pytest.fixture(autouse=True)
def quiet():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


def overhead(t):
    return SkyCoord(AltAz(alt=80 * u.deg, az=10 * u.deg, obstime=t, location=SITE)).icrs


def test_safe_target_at_night():
    assert check_target(overhead(NIGHT), NIGHT, SITE, Rules()) == []


def test_sun_is_never_a_target():
    sun = get_body("sun", DAY, SITE)
    reasons = check_target(SkyCoord(sun.ra, sun.dec), DAY, SITE, Rules(allow_daytime=True))
    assert any("from the Sun" in r for r in reasons)
    assert any("Sun is up" in r for r in check_target(overhead(DAY), DAY, SITE, Rules()))


def test_horizon_profile():
    low = SkyCoord(AltAz(alt=25 * u.deg, az=90 * u.deg, obstime=NIGHT, location=SITE)).icrs
    assert check_target(low, NIGHT, SITE, Rules()) == []
    rules = Rules(horizon=[(0, 10), (80, 30), (100, 30), (180, 10)])  # a building in the east
    assert any("below the limit" in r for r in check_target(low, NIGHT, SITE, rules))
    assert rules.horizon_alt(350) == 15 and abs(rules.horizon_alt(90) - 30) < 1e-9  # min_alt still applies
    assert abs(Rules(min_alt=0, horizon=[(350, 20), (10, 40)]).horizon_alt(0) - 30) < 1e-9  # wraps at 360


def test_weather_fails_closed():
    r = Rules()
    assert check_weather(True, {"humidity": 50, "windspeed": 3, "rainrate": 0.0}, r) == []
    assert check_weather(None, {}, r) == []  # no monitor, no sensors configured
    assert check_weather(False, {}, r) == ["safety monitor reports unsafe"]
    assert check_weather("error", {}, r) == ["safety monitor is not answering"]
    assert len(check_weather(True, {"humidity": 95, "windspeed": 20, "rainrate": 0.2}, r)) == 3
    assert check_weather(True, {"humidity": "error"}, r) == ["humidity sensor is not answering"]


def test_link_timeout():
    assert check_link({"mount": 5.0, "dome": 45.0}, Rules(link_timeout_s=30)) == ["dome has not answered for 45 s"]
