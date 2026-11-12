"""PER-14: νmax and Δν of a synthetic red giant, the scaling relations for the Sun."""

import numpy as np
import pytest

from astrowb.timeseries import seismology as sz


def red_giant(numax=100.0, dnu=9.0, seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(0, 200, 30 / 1440)  # 200 days, 30-min cadence
    ts = t * 86400
    y = np.zeros(t.size)
    for n in range(4, 20):
        for ell, shift in ((0, 0.0), (1, 0.5), (2, -0.12)):
            nu = (n + 1.4 + shift) * dnu  # ε = 1.4
            amp = 60 * np.exp(-0.5 * ((nu - numax) / (0.66 * numax**0.88 / 2.355)) ** 2) * (1, 1.3, 0.7)[ell]
            # finite lifetimes: a few close frequencies with random phases
            for d in rng.normal(0, 0.05, 3):
                y += amp / np.sqrt(3) * np.sin(2 * np.pi * (nu + d) * 1e-6 * ts + rng.uniform(0, 2 * np.pi))
    y += 80 * rng.normal(size=t.size)  # white noise, ppm
    return t, 1 + 1e-6 * y


def test_numax_dnu_and_scaling():
    t, flux = red_giant()
    f, p = sz.psd(t, flux, f_max=280)
    var = np.var((flux - 1) * 1e6)
    assert np.sum(p) * np.median(np.diff(f)) == pytest.approx(var, rel=1e-5)  # Parseval
    nu = sz.numax(f, p, 20, 250)
    assert nu == pytest.approx(100.0, rel=0.03)
    assert sz.dnu(f, p, nu) == pytest.approx(9.0, rel=0.03)
    assert sz.scaling(3090.0, 135.1, 5777.0) == pytest.approx((1.0, 1.0))
