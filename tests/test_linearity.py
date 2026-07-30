"""Linearity correction (PLAN 4.7 item 5): raw counts of a non-linear camera become proportional to the light."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.calibration import masters

POLY = (0.0, 1.0, 4e-6)  # true = v + 4e-6 v^2: the camera reads 4 % low at 10 000 ADU


def raw_from_true(true):
    """The value the camera writes for a true count (inverse of POLY)."""
    return (-1 + np.sqrt(1 + 4 * POLY[2] * true)) / (2 * POLY[2])


def test_linearity_makes_counts_proportional_to_exposure(tmp_path):
    rate = 900.0  # counts per second from a steady flat source
    times = [2, 5, 10, 20, 30]
    for t in times:
        fits.PrimaryHDU(np.full((20, 30), raw_from_true(rate * t), np.float32), fits.Header({"EXPTIME": t})).writeto(
            tmp_path / f"f{t}.fits"
        )
    plain = [masters.load(tmp_path / f"f{t}.fits")[0].mean() / t for t in times]
    with masters.linearity(POLY):
        corrected = [masters.load(tmp_path / f"f{t}.fits")[0].mean() / t for t in times]
        h = masters.load(tmp_path / f"f{times[0]}.fits")[1]
    assert np.ptp(plain) / np.mean(plain) > 0.05  # uncorrected: the rate falls as the counts rise
    assert np.ptp(corrected) / np.mean(corrected) < 1e-4 and np.mean(corrected) == pytest.approx(rate, rel=1e-4)
    assert h["LINCORR"] and "LINCORR" not in masters.load(tmp_path / f"f{times[0]}.fits")[1]  # off outside the block


def test_linearity_in_the_calibration_step(tmp_path):
    from astrowb.engine.steps import execute

    class Ctx:
        def progress(self, *a):
            pass

        def check(self):
            pass

    d = tmp_path / "night"
    d.mkdir()
    for i in range(3):
        fits.PrimaryHDU(
            np.full((20, 30), raw_from_true(300.0), np.float32), fits.Header({"IMAGETYP": "Bias Frame", "EXPTIME": 0.0})
        ).writeto(d / f"b{i}.fits")
    fits.PrimaryHDU(
        np.full((20, 30), raw_from_true(300.0 + 12000.0), np.float32),
        fits.Header({"IMAGETYP": "Light Frame", "EXPTIME": 60.0}),
    ).writeto(d / "l.fits")
    frames = execute("calibration.scan", {"folder": str(d)}, {}, Ctx())["frames"]
    out = execute(
        "calibration.run", {"frames": frames, "output_dir": str(tmp_path / "cal")}, {"linearity": POLY}, Ctx()
    )
    cal = fits.getdata(out["calibrated"][0])
    assert np.median(cal) == pytest.approx(12000.0, rel=1e-4)  # bias + signal corrected, then the bias removed
    with pytest.raises(masters.CalibrationError):
        with masters.linearity([5.0]):
            pass
