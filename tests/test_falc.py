"""PER-11: three nights with zero-point errors recover a double-peaked rotation."""

import numpy as np
import pytest

from astrowb.timeseries import falc


def test_three_nights_with_offsets():
    rng = np.random.default_rng(2)
    p = 5.3 / 24  # days
    t, nights = [], []
    for n, start in enumerate((0.0, 1.02, 3.05)):
        tt = start + np.linspace(0, 0.28, 120)
        t.append(tt)
        nights.append(np.full(tt.size, n))
    t, nights = np.concatenate(t), np.concatenate(nights)
    ph = 2 * np.pi * t / p
    mag = 0.25 * np.cos(2 * ph) + 0.05 * np.sin(ph) + 0.03 * np.cos(4 * ph)  # two maxima a rotation, unequal
    mag = 14.0 + mag + np.array([0.0, 0.05, -0.04])[nights] + rng.normal(0, 0.01, t.size)
    err = np.full(t.size, 0.01)
    _periods, rms, best = falc.search(t, mag, err, nights, 0.1, 0.4)
    assert best == pytest.approx(p, rel=2e-3)
    order = falc.best_order(t, mag, err, nights, best)
    assert order >= 4
    _r, _c, _k, coef, n = falc.fit(t, mag, err, nights, best, order)
    assert falc.amplitude(coef, n, order) == pytest.approx(0.56, abs=0.05)
    assert coef[1] - coef[0] == pytest.approx(0.05, abs=0.01)  # the night offsets come out with the fit
