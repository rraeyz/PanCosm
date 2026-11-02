"""OC-11: polynomial + sinusoid, a pulsator's period change in d/Myr."""

import numpy as np
import pytest

from astrowb.timeseries import ephemeris_models as em


def test_an_rr_lyrae_period_change_is_recovered():
    p, rate = 0.5667, 0.3  # days; dP/dt in d/Myr
    q = rate / 1e6 / 365.25 * p / 2  # T = T0 + P E + Q E²: dP/dt = 2Q/P (days per day)
    inside = 0
    for seed in range(100):
        rng = np.random.default_rng(seed)
        e = np.sort(rng.choice(np.arange(60000), 150, replace=False)).astype(float)  # 93 years of maxima
        t = 2440000.0 + p * e + q * e * e + rng.normal(0, 0.003, e.size)
        got, err = em.dp_dt_days_per_myr(em.fit(t, e, np.full(e.size, 0.003), 2))
        inside += abs(got - rate) < err
    assert 0.6 <= inside / 100 <= 0.78


def test_a_cyclic_term_is_found_and_measured():
    rng = np.random.default_rng(3)
    e = np.sort(rng.choice(np.arange(20000), 200, replace=False)).astype(float)
    t = 2450000.0 + 0.4 * e + 0.004 * np.sin(2 * np.pi * e / 7000 + 1.0) + rng.normal(0, 0.0005, e.size)
    f = em.find_cycle(t, e, np.full(e.size, 0.0005))
    (term,) = em.cyclic_terms(f)
    assert f["cycles"][0] == pytest.approx(7000, rel=0.02)
    assert term["amplitude"] == pytest.approx(0.004, abs=4 * term["amplitude_err"])
    assert term["phase"] == pytest.approx(1.0 / (2 * np.pi), abs=0.02)
    assert f["chi2r"] < 1.3
