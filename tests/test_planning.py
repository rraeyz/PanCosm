import warnings

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import TETE, SkyCoord
from astropy.time import Time

from astrowb import timing
from astrowb.planning.visibility import Site, airmass, altitudes, events, moon, night, night_grid, sun_altitude

ANKARA = Site("TUG-like", 36.82, 30.34, 2500.0)


@pytest.fixture(autouse=True)
def quiet():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield


def test_altitude_matches_spherical_formula():
    """Independent check: sin h = sin(phi) sin(dec) + cos(phi) cos(dec) cos(H), apparent coordinates."""
    star = SkyCoord("02h04m10.28s +46d41m16.2s")
    t = night_grid(ANKARA, "2026-11-15", 60)
    alt = altitudes(star, t, ANKARA)
    app = star.transform_to(TETE(obstime=t))
    lst = t.sidereal_time("apparent", longitude=ANKARA.lon * u.deg).rad
    phi, dec, ha = np.radians(ANKARA.lat), app.dec.rad, lst - app.ra.rad
    alt_formula = np.degrees(np.arcsin(np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.cos(ha)))
    assert np.max(np.abs(alt - alt_formula)) < 0.02  # deg; no refraction in either


def test_airmass():
    assert abs(airmass(90.0) - 1.0) < 1e-3
    assert abs(airmass(30.0) - 1.995) < 0.01
    assert 30 < airmass(0.5) < 40 and np.isnan(airmass(-1.0))


def test_twilight():
    dusk, dawn = night(ANKARA, "2026-11-15")
    for t in (dusk, dawn):
        assert abs(sun_altitude(Time([t]), ANKARA)[0] + 18) < 0.05
    assert 9 < (dawn - dusk).to_value(u.hour) < 12  # November at 37 deg N
    north = Site("Tromso", 69.65, 18.96)
    assert night(north, "2026-06-21") == (None, None)  # midnight sun: no astronomical night


def test_new_moon_at_solar_eclipse():
    m = moon(Time(["2024-04-08T18:18:00"]), Site("Mazatlan", 23.2, -106.4))
    assert m["illumination"][0] < 0.01


def test_events_found_and_timed():
    star = SkyCoord("02h04m10.28s +46d41m16.2s")
    dusk, dawn = night(ANKARA, "2026-11-15")
    mid_utc = dusk + (dawn - dusk) / 2
    mid_bjd = timing.bjd_tdb(mid_utc, star, ANKARA.location).jd
    p = 2.1500082
    ev = events(mid_bjd - 100 * p, p, star, ANKARA, dusk, dawn, duration_d=0.13)
    assert len(ev) == 1 and ev[0].kind == "primary"
    assert abs((ev[0].mid - mid_utc).sec) < 1  # BJD -> UTC conversion
    assert ev[0].fully_observable and ev[0].alt_mid > 50
    ev2 = events(mid_bjd - 100 * p + p / 2, p, star, ANKARA, dusk, dawn, secondary=True)
    assert [e.kind for e in ev2] == ["secondary"]


def test_resolver_coordinates_cache_and_offline(tmp_path):
    from astrowb.planning.targets import Resolver, Target, TargetError

    calls = []

    def fake_simbad(name):
        calls.append(name)
        if name == "offline star":
            raise ConnectionError("no network")
        return Target("HAT-P-32", 31.0428, 46.6878, 11.4, "SIMBAD")

    r = Resolver(tmp_path / "cache.json", online=fake_simbad)
    assert abs(r.resolve("02:04:10.3 +46:41:16").ra - 31.0429) < 1e-3  # typed, no lookup
    assert abs(r.resolve("31.0428 46.6878").dec - 46.6878) < 1e-9
    assert r.resolve("HAT-P-32").source == "SIMBAD"
    again = Resolver(tmp_path / "cache.json", online=fake_simbad).resolve("hat-p-32 ")
    assert again.source == "cache" and again.vmag == 11.4 and calls == ["HAT-P-32"]
    with pytest.raises(TargetError, match="local cache"):
        r.resolve("offline star")


def test_planets_and_the_moon_are_followed_through_the_night(tmp_path):
    from astropy.coordinates import get_body

    from astrowb.planning.steps import night_step
    from astrowb.planning.targets import Resolver, body_of

    assert body_of("Satürn") == "saturn" and body_of(" AY ") == "moon" and body_of("Vega") is None
    sat = Resolver(tmp_path / "t.json", online=lambda n: pytest.fail("planets are not looked up")).resolve("Saturn")
    assert sat.source == "solar system"

    class Ctx:
        def progress(self, *a):
            pass

    site = {"name": "TUG", "lat": 36.824, "lon": 30.335, "height": 2500.0}
    targets = [{"name": "Saturn", "ra": 0.0, "dec": 0.0}, {"name": "Ay", "ra": 0.0, "dec": 0.0}]
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # the Moon distance must not warn about frames
        inputs = {"site": site, "date": "2026-04-15", "targets": targets}
        night = night_step(inputs, {"min_alt": 20.0, "step_min": 30.0}, Ctx())
    saturn, moon_target = night["night"]["targets"]
    assert saturn["body"] == "saturn" and moon_target["body"] == "moon"
    assert np.allclose(moon_target["alt"], night["night"]["moon_alt"])  # the stored (0, 0) is not used
    times = Time(night["night"]["jd"], format="jd")
    s = Site(**site)
    assert np.allclose(saturn["alt"], altitudes(get_body("saturn", times, s.location), times, s), atol=1e-6)
