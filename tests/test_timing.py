import warnings

import astropy.units as u
import pytest
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.io import fits
from astropy.time import Time

from astrowb import timing

# Header of a real MicroObservatory frame (EXOTIC sample data, HAT-P-32, 2017-12-20)
MICROOBS = fits.Header(
    {
        "DATE-OBS": "2017-12-19T18:33:43.317-0700",
        "UT-OBS": "2017-12-20T01:33:43.317-0000",
        "MJD-OBS": 58107.065,
        "EXPTIME": 60.0,
    }
)


def test_local_time_with_offset_is_converted_to_utc():
    h = MICROOBS.copy()
    del h["UT-OBS"]
    assert abs((timing.start_time(h) - Time("2017-12-20T01:33:43.317")).sec) < 1e-3


def test_mid_exposure_and_keyword_preference():
    t = timing.mid_time(MICROOBS)
    assert abs((t - Time("2017-12-20T01:34:13.317")).sec) < 1e-3  # start + 30 s, not the rounded MJD-OBS


@pytest.mark.parametrize(
    "header",
    [
        {"DATE-OBS": "2017-12-20", "TIME-OBS": "01:33:43.317"},
        {"DATE-OBS": "2017-12-20T01:33:43.317Z"},
        {"JD": 2458107.5650846875},
    ],
)
def test_other_conventions(header):
    assert abs((timing.start_time(fits.Header(header)) - Time("2017-12-20T01:33:43.317")).sec) < 0.01


def test_missing_time():
    with pytest.raises(timing.TimeError):
        timing.start_time(fits.Header({"EXPTIME": 1.0}))


def test_bjd_tdb_consistent():
    target = SkyCoord("02h04m10.28s +46d41m16.2s")
    t = Time("2017-12-20T02:00:00", scale="utc")
    bjd = timing.bjd_tdb(t, target)
    hjd = timing.hjd(t, target)
    tt_minus_utc = 69.184  # s in 2017 (37 leap seconds + 32.184)
    ltt = (bjd.jd - t.jd) * 86400 - tt_minus_utc
    assert abs(ltt) < 500  # light travel time across Earth's orbit is at most ~8.3 min
    assert abs((bjd.jd - hjd.jd) * 86400 - tt_minus_utc) < 8  # Sun vs barycentre: a few seconds
    site = EarthLocation.from_geodetic(-110.88 * u.deg, 31.68 * u.deg, 2300 * u.m)
    assert abs((timing.bjd_tdb(t, target, site) - bjd).sec) < 0.025  # observatory adds < 21 ms


def test_location_from_header():
    loc = timing.location(fits.Header({"SITELAT": "31:40:48", "SITELONG": "-110:52:48", "SITEELEV": 2300}))
    assert abs(loc.lat.deg - 31.68) < 1e-6 and abs(loc.lon.deg + 110.88) < 1e-6
    assert timing.location(fits.Header({"LATITUDE": 31.68, "LONGITUD": 110.88})) is None  # ambiguous sign


def test_airmass_offline():
    site = EarthLocation.from_geodetic(-110.88 * u.deg, 31.68 * u.deg, 2300 * u.m)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        am = timing.airmass(Time("2017-12-20T01:34:13"), SkyCoord("02h04m10s +46d41m16s"), site)
    assert 1.0 < am < 1.3  # header TELALT = 62.6 deg -> sec z = 1.126


def test_chronological_order(tmp_path):
    import numpy as np

    names = {
        "light_1.fits": "2026-01-01T00:01:00",
        "light_10.fits": "2026-01-01T00:10:00",
        "light_2.fits": "2026-01-01T00:02:00",
        "notime.fits": None,
    }
    for name, date in names.items():
        h = fits.Header({"DATE-OBS": date} if date else {})
        fits.PrimaryHDU(np.zeros((2, 2), np.float32), h).writeto(tmp_path / name)
    order = [p.split("/")[-1].split("\\")[-1] for p in timing.chronological(tmp_path.glob("*.fits"))]
    assert order == ["light_1.fits", "light_2.fits", "light_10.fits", "notime.fits"]
