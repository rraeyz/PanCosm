"""EXO-8: the RM anomaly's symmetry, amplitude and the obliquity recovered."""

import numpy as np
import pytest
from scipy.optimize import least_squares

from astrowb.exoplanets import rm

P, A, K, INC = 3.0, 8.0, 0.1, 88.0


def test_aligned_misaligned_and_amplitude():
    t = np.linspace(-0.08, 0.08, 41)
    aligned = rm.anomaly(t, P, 0.0, K, A, INC, 5000.0, 0.0)
    assert np.allclose(aligned, -aligned[::-1], atol=1e-6 * 5000)  # antisymmetric about mid-transit
    assert aligned[10] < 0 < aligned[30] or aligned[10] > 0 > aligned[30]
    # a small planet near the limb of a uniform disc: |ΔV| ≈ k² v sin i x / (1 − k²)
    one = rm.anomaly([0.03], P, 0.0, K, A, 90.0, 5000.0, 0.0, "uniform", ())[0]
    x = A * np.sin(2 * np.pi * 0.03 / P)
    assert abs(one) == pytest.approx(K**2 * 5000 * x / (1 - K**2), rel=0.03)
    polar = rm.anomaly(t, P, 0.0, K, A, INC, 5000.0, 90.0)
    assert np.all(polar[np.abs(t) < 0.06] * polar[20] >= 0)  # one sign all through: the planet crosses one side


def test_the_obliquity_is_recovered():
    rng = np.random.default_rng(0)
    t = np.linspace(-0.09, 0.09, 60)
    truth = 35.0
    v = rm.anomaly(t, P, 0.0, K, A, INC, 6000.0, truth) + rng.normal(0, 3.0, t.size)
    sol = least_squares(lambda p: rm.anomaly(t, P, 0.0, K, A, INC, p[0], p[1]) - v, [4000.0, 0.0],
                        diff_step=1e-3)  # fmt: skip
    cov = np.linalg.inv(sol.jac.T @ sol.jac) * np.sum(sol.fun**2) / (t.size - 2)
    assert abs(sol.x[1] - truth) < 3 * np.sqrt(cov[1, 1])  # one realisation: 1.9 σ here
    exact = rm.anomaly(t, P, 0.0, K, A, INC, 6000.0, truth)
    clean = least_squares(lambda p: rm.anomaly(t, P, 0.0, K, A, INC, p[0], p[1]) - exact, [4000.0, 0.0],
                          diff_step=1e-3)  # fmt: skip
    assert clean.x[1] == pytest.approx(truth, abs=0.01) and clean.x[0] == pytest.approx(6000, rel=1e-4)
