"""PER-2: detrending that keeps the transits, against wotan's biweight on a stored curve."""

from pathlib import Path

import numpy as np
import pytest

from astrowb.timeseries import clean

REFERENCE = Path(__file__).parent / "validation" / "data" / "wotan_biweight.txt"


def test_the_biweight_equals_the_reference_implementation():
    t, y, ref = np.loadtxt(REFERENCE).T
    assert np.max(np.abs(clean.trend(t, y, "biweight", 0.5, gap=0.5) - ref)) < 1e-6


def synthetic(seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(0, 20, 2 / 1440)  # 2-minute cadence, 20 days
    t = t[(t % 10) < 9]  # a gap: two segments
    slow = 0.02 * np.sin(2 * np.pi * t / 15) + 0.004 * t
    transit = clean.event_mask(t, 3.1, 1.2, 0.12, factor=1.0)
    y = (1 + slow) * (1 - 0.01 * transit) + rng.normal(0, 0.001, t.size)
    bad = rng.choice(t.size, 40, replace=False)
    y[bad] += rng.choice([-1, 1], 40) * 0.03
    return t, y, slow, transit, bad


@pytest.mark.parametrize("method", ["biweight", "median", "spline"])
def test_the_transit_safe_preset_keeps_the_depth(method):
    t, y, slow, transit, bad = synthetic()
    mask = clean.event_mask(t, 3.1, 1.2, 0.12)  # the events masked from the trend and from the outlier search
    out = clean.outliers(y - clean.trend(t, y, "median", 0.3, mask=mask), 5.0) & ~mask
    tr = clean.trend(t, y, method, 0.5, mask=mask | out)
    flat = y / tr
    depth = np.median(flat[~transit & ~out]) - np.median(flat[transit & ~out])
    assert depth == pytest.approx(0.01, rel=0.03)
    resid = tr[~transit] - (1 + slow[~transit])
    assert np.std(resid) < 0.001 and set(np.flatnonzero(out)) >= set(bad[~mask[bad]])


def test_polynomial_savgol_segments_nights_and_directions():
    t = np.linspace(0, 1, 400)
    y = 1 + 0.3 * t - 0.2 * t**2 + np.random.default_rng(2).normal(0, 1e-3, t.size)
    assert np.std(clean.trend(t, y, "polynomial") - (1 + 0.3 * t - 0.2 * t**2)) < 3e-4
    assert np.std(clean.trend(t, y, "savgol", 51) - (1 + 0.3 * t - 0.2 * t**2)) < 5e-4
    nights = np.concatenate([np.linspace(0, 0.3, 50), np.linspace(1, 1.3, 50)])
    level = np.where(nights < 0.5, 1.0, 1.05)
    assert list(np.unique(clean.segments(nights))) == [0, 1]
    assert np.allclose(clean.nightly_means(nights, level), level)
    flare = np.r_[np.zeros(50), 1.0, -1.0, np.zeros(50)] + np.random.default_rng(3).normal(0, 0.01, 102)
    assert list(np.flatnonzero(clean.outliers(flare, direction="up"))) == [50]
    assert list(np.flatnonzero(clean.outliers(flare, direction="down"))) == [51]
    with pytest.raises(ValueError):
        clean.trend(t, y, "fourier")
