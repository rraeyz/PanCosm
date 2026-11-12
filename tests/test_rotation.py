"""PER-15: rotation periods by the ACF, flares found completely and rarely invented."""

import numpy as np
import pytest

from astrowb.timeseries import rotation as rot


def spotted(seed, period, n_days=27, cadence=0.02):
    rng = np.random.default_rng(seed)
    t = np.arange(0, n_days, cadence)
    t = t[(t < 13) | (t > 14)]  # an orbit gap
    amp = 0.01 * (1 + 0.3 * np.sin(2 * np.pi * t / 40))  # spots evolve
    y = 1 + amp * np.sin(2 * np.pi * t / period) + 0.4 * amp * np.sin(4 * np.pi * t / period + 1)
    return t, y + rng.normal(0, 0.002, t.size)


def test_rotation_periods():
    for seed, p in enumerate((1.7, 3.4, 6.1)):
        t, y = spotted(seed, p)
        assert rot.acf_period(t, y, max_lag=12) == pytest.approx(p, rel=0.05)


def test_flares():
    rng = np.random.default_rng(5)
    t = np.arange(0, 20, 2 / 1440)
    y = 1 + 0.005 * np.sin(2 * np.pi * t / 2.3) + rng.normal(0, 0.001, t.size)
    peaks = np.sort(rng.uniform(0.5, 19.5, 30))
    for p in peaks:  # 6σ and more, a fast rise and an exponential decay
        after = t >= p
        y[after] += rng.uniform(0.006, 0.03) * np.exp(-(t[after] - p) / 0.01)
    found = rot.flares(t, y)
    hit = sum(any(abs(f["peak"] - p) < 0.01 for f in found) for p in peaks)
    false = sum(not any(abs(f["peak"] - p) < 0.01 for p in peaks) for f in found)
    assert hit >= 27 and false <= 0.05 * len(found) + 1
    assert all(f["ed"] > 0 for f in found)


def test_two_spots_half_a_rotation_apart():
    rng = np.random.default_rng(9)
    t = np.arange(0, 27, 0.02)
    p = 4.0
    # the second harmonic strong enough to make a peak at P/2, lower than the one at P: P is taken
    y = 1 + 0.01 * np.sin(2 * np.pi * t / p) + 0.009 * np.sin(4 * np.pi * t / p) + rng.normal(0, 0.001, t.size)
    assert rot.acf_period(t, y, max_lag=12) == pytest.approx(p, rel=0.05)
