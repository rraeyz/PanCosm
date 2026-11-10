"""CAL-13: over 30 repeated lights the empirical variance equals the propagated variance plane within 3 % on the sky
and on a bright star; a saturated star, a hot pixel and a cosmic ray stay flagged through calibration and a 0.4 px
shift; a plain FITS still reads."""

import numpy as np
import pytest
from astropy.io import fits

from astrowb.core import planes

GAIN, RN, SHAPE = 1.6, 7.0, (60, 70)


def raw(rng, signal):
    electrons = rng.poisson(np.clip(signal, 0, None) * GAIN)
    return electrons / GAIN + rng.normal(0, RN / GAIN, signal.shape)


def test_the_variance_plane_matches_the_scatter():
    rng = np.random.default_rng(1)
    yy, xx = np.indices(SHAPE)
    bias_level, dark_level = 500.0, 40.0
    flat_true = 1 + 0.05 * (xx / SHAPE[1])
    star = 30000 * np.exp(-((xx - 35) ** 2 + (yy - 30) ** 2) / (2 * 2.0**2))
    sky = (800 + star) * flat_true
    bias = planes.master([bias_level + rng.normal(0, RN / GAIN, SHAPE) for _ in range(25)])
    dark = planes.master([bias_level + dark_level + rng.normal(0, RN / GAIN, SHAPE) for _ in range(25)])
    dark = planes.Frame(dark.sci - bias.sci, dark.var + bias.var, dark.dq)  # a bias-subtracted master dark
    flat = planes.master([raw(rng, 20000 * flat_true) for _ in range(20)])
    # the masters are shared by all 30 frames: their part does not scatter between frames, so the plane compared
    # here is the frames' own (the masters' variances set to zero); the full plane is that plus the masters' part
    quiet = [planes.Frame(m.sci, np.zeros(SHAPE), m.dq) for m in (bias, dark, flat)]
    outs, own = [], []
    for _ in range(30):
        f = planes.Frame.from_raw(bias_level + raw(rng, sky + dark_level), GAIN, RN, bias_level=bias_level)
        outs.append(planes.calibrate(f, bias, dark, 1.0, flat))
        own.append(planes.calibrate(f, *quiet[:2], 1.0, quiet[2]).var)
    empirical = np.array([o.sci for o in outs]).var(axis=0, ddof=1)
    plane = np.mean(own, axis=0)
    assert np.all(np.mean([o.var for o in outs], axis=0) > plane)  # the masters' part is in the full plane
    sky_px = np.hypot(xx - 35, yy - 30) > 12
    star_px = np.hypot(xx - 35, yy - 30) < 4
    assert np.mean(empirical[sky_px] / plane[sky_px]) == pytest.approx(1.0, rel=0.03)
    assert np.mean(empirical[star_px] / plane[star_px]) == pytest.approx(1.0, rel=0.1)  # 49 px × 29 dof


def test_flags_survive_calibration_and_a_shift(tmp_path):
    rng = np.random.default_rng(2)
    data = 1000 + rng.normal(0, 5, SHAPE)
    data[20:23, 30:33] = 65535  # a saturated star's core
    f = planes.Frame.from_raw(data, GAIN, RN, saturation=65000)
    f.dq[40, 10] |= planes.BAD  # a hot pixel from the bad-pixel mask
    f.dq[10, 50] |= planes.COSMIC
    out = planes.shift(planes.calibrate(f), 0.4, 0.0)
    assert (out.dq[20:23, 31:33] & planes.SATURATED).all()
    assert out.dq[40, 10] & planes.BAD and out.dq[40, 11] & planes.BAD  # both pixels the 0.4 px shift touched
    assert out.dq[10, 50] & planes.COSMIC and (out.dq[:, 0] & planes.NODATA).all()
    assert out.header["VARCORR"] > 1  # resampling correlated the pixels
    path = planes.write(tmp_path / "f.fits", out)
    back = planes.read(path)
    assert np.array_equal(back.dq, out.dq) and np.allclose(back.var, out.var, rtol=1e-6)
    fits.PrimaryHDU(np.ones((4, 4), np.float32)).writeto(tmp_path / "plain.fits")
    plain = planes.read(tmp_path / "plain.fits")
    assert plain.var is None and plain.dq is None and plain.sci.shape == (4, 4)
