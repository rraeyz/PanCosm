"""PER-13: bands sampled apart searched together."""

import numpy as np
import pytest

from astrowb.timeseries import methods


def rrab(phase):
    return sum(-((-1) ** k) / k * np.sin(2 * np.pi * k * phase) for k in range(1, 5))


def test_the_joint_search_finds_the_period_of_two_sparse_bands():
    rng = np.random.default_rng(4)
    p = 0.5712
    tg = np.sort(rng.choice(np.arange(400), 35, replace=False) + rng.uniform(0.3, 0.5, 35))  # nightly, sparse
    tr = np.sort(rng.choice(np.arange(400), 35, replace=False) + rng.uniform(0.3, 0.5, 35))
    yg = 15.0 + 0.4 * rrab(tg / p) + rng.normal(0, 0.03, tg.size)
    yr = 14.7 + 0.3 * rrab(tr / p) + rng.normal(0, 0.03, tr.size)  # another mean and amplitude
    t, y = np.r_[tg, tr], np.r_[yg, yr]
    band = np.r_[np.full(tg.size, "g"), np.full(tr.size, "r")]
    _periods, power, best = methods.multiband(t, y, band, p_min=0.2, p_max=2.0, n_base=2, n_band=1)
    assert best == pytest.approx(p, rel=1e-4)
    assert 0 <= power.min() and power.max() <= 1
