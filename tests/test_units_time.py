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
