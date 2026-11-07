"""PHO-34: the scatter ratio, β, and the noise budget."""

import numpy as np
import pytest

from astrowb.photometry import errors


def test_white_and_red_noise():
    rng = np.random.default_rng(1)
    white = rng.normal(0, 0.002, 4000)
    ratio, offer = errors.scatter_ratio(white, np.full(4000, 0.002))
    assert ratio == pytest.approx(1.0, abs=0.05) and offer is None
    ratio, offer = errors.scatter_ratio(white, np.full(4000, 0.0015))
    assert offer == pytest.approx(1.33, abs=0.03)
    assert errors.beta_factor(white, [5, 10, 20, 40]) == pytest.approx(1.0, abs=0.1)
    # red noise of known amplitude: a random walk smoothed to 30 points, its binned RMS predicts β
    red = white + np.convolve(rng.normal(0, 0.0015, 4000), np.ones(30) / np.sqrt(30), "same")
    rows = errors.rms_vs_bin(red, [20])
    expected = rows[0][1] / rows[0][2]
    assert errors.beta_factor(red, [20]) == pytest.approx(expected, rel=1e-9)
    assert expected > 1.3


def test_budget():
    parts, rel = errors.budget(1e5, 50, 1, 8, 80, 0.001)
    assert parts["photon"] == 1e5 and parts["read"] == 80 * 64
    assert rel == pytest.approx(np.sqrt(1e5 + 4000 + 80 + 5120 + 1e4) / 1e5)


def test_point_to_point_ratio_ignores_a_transit():
    rng = np.random.default_rng(1)
    t = np.linspace(0, 1, 600)
    f = 1 + rng.normal(0, 0.003, t.size) - 0.02 * (np.abs(t - 0.5) < 0.1)  # a 2 % transit
    ratio, factor = errors.point_to_point_ratio(f, np.full(t.size, 0.003))
    assert ratio == pytest.approx(1.0, abs=0.08) and factor is None
    ratio, factor = errors.point_to_point_ratio(f, np.full(t.size, 0.002))
    assert factor == pytest.approx(1.5, abs=0.12)
    assert errors.point_to_point_ratio([1.0] * 5, [0.1] * 5) == (None, None)
