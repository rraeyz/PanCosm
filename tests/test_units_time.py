"""ARC-15: header times in their own time system, mid-exposure from the right keywords, one airmass function."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb import timing
from astrowb.core.units import AIRMASS_FORMULAS, airmass


def header(**cards):
    h = fits.Header({"DATE-OBS": "2024-03-01T22:00:00", "EXPTIME": 60.0})
    h.update(cards)
    return h


def test_timesys_is_honoured():
    utc = timing.start_time(header())
    tt = timing.start_time(header(TIMESYS="TT"))
    assert (utc - tt).to_value("sec") == pytest.approx(69.184, abs=1e-3)  # TT runs 69.184 s ahead since 2017
    gps = timing.start_time(header(TIMESYS="GPS"))
    assert (utc - gps).to_value("sec") == pytest.approx(18.0, abs=1e-3)  # GPS = UTC + 18 s since 2017
    jd = timing.start_time(fits.Header({"JD": 2460371.5, "TIMESYS": "TT"}))
    assert (jd.utc.jd - 2460371.5) * 86400 == pytest.approx(-69.184, abs=1e-3)
    with pytest.raises(timing.TimeError, match="TIMESYS"):
        timing.start_time(header(TIMESYS="LOCAL"))


def test_mid_exposure_from_the_best_keywords():
    start = timing.start_time(header())
    assert (timing.mid_time(header()) - start).to_value("sec") == pytest.approx(30)
    dead = header(**{"DATE-END": "2024-03-01T22:01:10"})  # 70 s from start to end for 60 s of light: the midpoint
    assert (timing.mid_time(dead) - start).to_value("sec") == pytest.approx(35)
    other = header(**{"DATE-END": "2024-03-01T22:30:00"})  # far from EXPTIME: not the same exposure's end
    assert (timing.mid_time(other) - start).to_value("sec") == pytest.approx(30)
    avg = header(**{"MJD-AVG": 60370.9170, "TIMESYS": "UTC"})
    assert timing.mid_time(avg).mjd == pytest.approx(60370.9170)


def test_airmass_formulas_agree_high_and_young_is_the_default():
    alts = np.arange(30, 90.1, 5)
    ref = airmass(alts)
    for f in (
        AIRMASS_FORMULAS
    ):  # the published formulas agree within 0.2 % above 30° (Hardie 0.14 % high at 30°); sec z is 0.4 % high
        assert np.allclose(airmass(alts, f), ref, rtol=2e-3 if f != "secz" else 5e-3), f
    assert np.allclose(airmass(alts[alts >= 55], "secz"), ref[alts >= 55], rtol=1e-3)
    assert airmass(90) == pytest.approx(1.0, abs=1e-4)
    assert airmass(10, "secz") / airmass(10) == pytest.approx(1.03, abs=0.01)  # sec z 3 % too large at 10°
    assert airmass(10, "kastenyoung1989") == pytest.approx(5.60, abs=0.02)  # Kasten & Young's table, z = 80°
    assert np.isfinite(airmass(0.5)) and np.isnan(airmass(-1))
    with pytest.raises(ValueError):
        airmass(45, "guess")


def test_a_stack_is_dated_by_all_its_frames(tmp_path):
    from astrowb.calibration.stacking import _stack_times

    paths = []
    for i in range(3):
        h = fits.Header({"DATE-OBS": f"2024-03-01T22:0{2 * i}:00", "EXPTIME": 60.0, "TIMESYS": "TT"})
        paths.append(tmp_path / f"f{i}.fits")
        fits.PrimaryHDU(np.zeros((4, 4), np.float32), h).writeto(paths[-1])
    stack = fits.getheader(paths[0])
    _stack_times(stack, [str(p) for p in paths], None)
    first = timing.mid_time(fits.getheader(paths[0]))
    assert (timing.mid_time(stack) - first).to_value("sec") == pytest.approx(120, abs=1e-3)  # the middle frame
    assert stack["DATE-END"].startswith("2024-03-01T22:05:00") and stack["TIMESYS"] == "TT"
    _stack_times(stack, [str(p) for p in paths], [1.0, 0.0, 0.0])  # weights: only the first frame counts
    assert (timing.mid_time(stack) - first).to_value("sec") == pytest.approx(0, abs=1e-3)


def test_time_standards_round_trip_and_agree_with_timing():
    from astropy import units as u
    from astropy.coordinates import EarthLocation, SkyCoord
    from astropy.time import Time

    from astrowb.core.units import STANDARDS, convert_times

    target, site = SkyCoord(10 * u.deg, 20 * u.deg), EarthLocation.from_geodetic(30 * u.deg, 37 * u.deg, 1000 * u.m)
    out = convert_times([2460512.5], "JD_UTC", target, site)
    ref = timing.bjd_tdb(Time([2460512.5], format="jd", scale="utc"), target, site).jd[0]
    assert (out["BJD_TDB"][0] - ref) * 86400 == pytest.approx(0, abs=1e-6)
    assert (out["JD_TT"][0] - 2460512.5) * 86400 == pytest.approx(69.184, abs=1e-3)
    for standard in STANDARDS:  # every standard back to UTC
        back = convert_times(out[standard], standard, target, site)
        assert (back["JD_UTC"][0] - 2460512.5) * 86400 == pytest.approx(0, abs=1e-4), standard
    assert 0 < out["alt"][0] < 90 and out["airmass"][0] >= 1
    many = 2460512.5 + np.linspace(0, 10, 5000)  # interpolated light times: within 0.1 ms of the direct ones
    fast = convert_times(many, "JD_UTC", target, site)["BJD_TDB"][::250]
    direct = convert_times(many[::250], "JD_UTC", target, site)["BJD_TDB"]
    assert np.abs(fast - direct).max() * 86400 < 1e-4


def test_converter_window(qapp, tmp_path):
    from astrowb.settings import Settings
    from astrowb.ui.converter_dialog import ConverterDialog

    d = ConverterDialog(Settings(tmp_path))
    d.target.setText("02:04:10.3 +46:41:16")
    d.times.setPlainText("2460512.5\n2460512.6")
    d.convert()
    assert d.table.rowCount() == 2 and d.table.item(0, 0).text() == "2460512.500000"
    assert d.text().splitlines()[0].startswith("JD_UTC\tMJD_UTC") and len(d.text().splitlines()) == 3
    d.times.setPlainText("")
    assert d.convert() is None and d.status.text()
