"""ARC-1: an old Earth-orientation table never stops alt-az computations; newer tables can be downloaded and used."""

import datetime as dt
from unittest import mock

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.time import Time
from astropy.utils import iers

from astrowb import timing
from astrowb.core import earth_orientation
from astrowb.devices import safety
from astrowb.planning import visibility

SITE = visibility.Site("test", 39.0, 30.0, 1000.0)
STAR = SkyCoord(10 * u.deg, 20 * u.deg)


def _three_years_later():
    """A clock far beyond the bundled table's measured part: what an old installation meets."""
    table = iers.earth_orientation_table.get()
    measured = float(table.meta.get("predictive_mjd") or table["MJD"][-1].value)
    return Time(measured + 3 * 365, format="mjd")


def test_alt_az_works_with_a_table_years_old():
    now = _three_years_later()
    night = Time(now.mjd - 0.3, format="mjd")
    with mock.patch.object(Time, "now", return_value=now):
        x = timing.airmass(night, STAR, SITE.location)
        alt = visibility.altitudes(STAR, night + np.arange(3) * u.hour, SITE)
        reasons = safety.check_target(STAR, night, SITE.location, safety.Rules())
    assert np.isfinite(x)
    assert np.all(np.isfinite(np.asarray(alt, float)))
    assert isinstance(reasons, list)


def test_bjd_does_not_depend_on_the_table_age():
    t = Time("2026-03-01T22:00:00", scale="utc")
    fresh = timing.bjd_tdb(t, STAR, EarthLocation.from_geodetic(0 * u.deg, 51.48 * u.deg)).jd
    with mock.patch.object(Time, "now", return_value=_three_years_later()):
        old = timing.bjd_tdb(t, STAR, EarthLocation.from_geodetic(0 * u.deg, 51.48 * u.deg)).jd
    assert fresh == old


def test_refresh_installs_a_downloaded_table_and_keeps_the_old_one_on_bad_data(tmp_path, monkeypatch):
    import astropy_iers_data as data

    monkeypatch.setenv("ASTROWB_CONFIG_DIR", str(tmp_path))
    good = {
        data.IERS_A_URL: open(data.IERS_A_FILE, "rb").read(),  # noqa: SIM115
        data.IERS_LEAP_SECOND_URL: open(data.IERS_LEAP_SECOND_FILE, "rb").read(),  # noqa: SIM115
    }
    before = iers.earth_orientation_table.get()

    def broken(url, timeout):
        return b"<html>proxy error</html>"

    with pytest.raises(Exception):  # noqa: B017 (astropy's parse error type is not part of its API)
        earth_orientation.refresh(fetch=broken)
    assert iers.earth_orientation_table.get() is before
    assert not (tmp_path / "earth-orientation" / "finals2000A.all").exists()

    def unreachable_then_mirror(url, timeout):
        if url in (data.IERS_A_URL, data.IERS_LEAP_SECOND_URL):
            raise OSError("no route")
        return good[{data.IERS_A_URL_MIRROR: data.IERS_A_URL}.get(url, data.IERS_LEAP_SECOND_URL)]

    try:
        st = earth_orientation.refresh(fetch=unreachable_then_mirror)
        assert (tmp_path / "earth-orientation" / "finals2000A.all").exists()
        assert st["source"] == "downloaded"
        assert not earth_orientation.due(dt.date.today())
        assert earth_orientation.due(dt.date.today() + dt.timedelta(days=8))
    finally:
        iers.earth_orientation_table.set(before)
