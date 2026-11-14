"""PLN-14: the Plan window's almanac against JPL Horizons at four sites over one day (2026-11-14, every 10 minutes;
data/planning/horizons_almanac.csv, made again by scripts/horizons/almanac.py): the Sun's and the Moon's altitude and
azimuth (airless, topocentric), the Moon's illuminated fraction, and the times the Sun's centre crosses 0°, −6°,
−12° and −18°. Horizons' table is on a 10-minute grid, so its crossing times are linear interpolations (a few
seconds off at most at these latitudes)."""

import csv
from pathlib import Path

import astropy.units as u
import numpy as np
import pytest
from astropy.time import Time

from astrowb.planning.visibility import Site, _crossings, moon, sun_altitude

REF = Path(__file__).parent / "data" / "planning" / "horizons_almanac.csv"
SITES = {
    "Ankara": Site("Ankara", 39.84, 32.78, 1250.0),
    "La Palma": Site("La Palma", 28.76, -17.88, 2330.0),
    "Siding Spring": Site("Siding Spring", -31.27, 149.07, 1160.0),
    "Mauna Kea": Site("Mauna Kea", 19.82, -155.47, 4200.0),
}
pytestmark = pytest.mark.validation


def reference(site, body):
    with REF.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["site"] == site and r["body"] == body]
    times = Time([f"2026-11-14T{r['utc'][-5:]}" for r in rows[:-1]] + ["2026-11-15T00:00"])
    return times, {k: np.array([float(r[k]) for r in rows]) for k in ("az", "alt", "illum")}


def angle(a, b):
    return np.abs((np.asarray(a) - np.asarray(b) + 180) % 360 - 180)


@pytest.mark.parametrize("name", SITES)
def test_sun_and_moon_against_horizons(name, measured):
    site = SITES[name]
    t, sun = reference(name, "sun")
    ours = sun_altitude(t, site)
    d_sun = float(np.max(np.abs(ours - sun["alt"])))
    _, mo = reference(name, "moon")
    m = moon(t, site)
    d_alt = float(np.max(np.abs(m["alt"] - mo["alt"])))
    up = mo["alt"] > 5  # the azimuth is ill-defined only at the zenith; it is checked where the Moon is up
    d_az = float(np.max(angle(m["az"][up], mo["az"][up]))) if up.any() else 0.0
    d_ill = float(np.max(np.abs(100 * m["illumination"] - mo["illum"])))
    for quantity, value, tol in (
        ("Sun altitude (deg)", d_sun, 0.005),
        ("Moon altitude (deg)", d_alt, 0.005),
        ("Moon azimuth above 5° (deg)", d_az, 0.02),
        ("Moon illuminated fraction (%)", d_ill, 0.05),
    ):
        measured("planning", f"{quantity}, {name}", "JPL Horizons", f"{tol}", value, value <= tol,
                 data=REF.name, step="planning.night")  # fmt: skip
        assert value <= tol, (quantity, value)


@pytest.mark.parametrize("name", SITES)
def test_twilight_times_against_horizons(name, measured):
    site = SITES[name]
    t, sun = reference(name, "sun")
    fine = Time("2026-11-14T00:00") + np.arange(0, 24 * 60 + 1) * u.min
    ours_alt = sun_altitude(fine, site)
    worst = 0.0
    for level in (0.0, -6.0, -12.0, -18.0):
        theirs = _crossings(t, sun["alt"], level)
        ours = _crossings(fine, ours_alt, level)
        for kind in ("down", "up"):
            assert len(theirs[kind]) == len(ours[kind]), (level, kind)
            for a, b in zip(theirs[kind], ours[kind], strict=True):
                worst = max(worst, abs((a - b).sec))
    measured("planning", f"Sun crossing 0/−6/−12/−18°, {name} (s)", "JPL Horizons (10-min grid)", "5",
             worst, worst <= 5, data=REF.name, step="planning.night")  # fmt: skip
    assert worst <= 5
