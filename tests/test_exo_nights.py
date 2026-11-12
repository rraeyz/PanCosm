"""EXO-9: three nights with their own trends fitted together."""

import numpy as np
import pytest

from astrowb.exoplanets import multi_night as mn
from astrowb.occult.model import transit

P, T0, K, A, B = 2.15, 2459000.5, 0.12, 8.0, 0.3


def night(n_cycle, trend, seed, sigma=0.0015):
    rng = np.random.default_rng(seed)
    tc = T0 + n_cycle * P
    t = np.linspace(tc - 0.12, tc + 0.12, 250)
    inc = np.degrees(np.arccos(B / A))
    f = transit(t - T0, P, 0.0, K, A, inc, "quadratic", (0.4, 0.2)) * (1 + trend * (t - t.mean()))
    return t, f + rng.normal(0, sigma, t.size), np.full(t.size, sigma)


def test_three_nights_give_the_ephemeris_and_a_sharper_radius():
    nights = [night(0, 0.02, 1), night(7, -0.03, 2), night(15, 0.05, 3)]
    start = {"t0": T0 + 0.002, "k": 0.1, "a_rs": 7.0, "b": 0.4}
    both = mn.fit(nights, P + 2e-4, start)
    assert both["period"] == pytest.approx(P, abs=3 * both["period_err"])
    assert both["t0"] == pytest.approx(T0, abs=3 * both["t0_err"])
    assert both["k"] == pytest.approx(K, abs=3 * both["k_err"]) and both["chi2r"] < 1.2
    singles = [
        mn.fit([n], P, {**start, "t0": T0 + c * P}, free_midtimes=True) for n, c in zip(nights, (0, 7, 15), strict=True)
    ]
    errs = [s["k_err"] for s in singles]
    # better than any single night, by about √N (single nights sit in the b–a/R★ valley at platform-dependent
    # places, so their errors scatter: 1.34 × the √N value seen on macOS)
    assert both["k_err"] < min(errs)
    assert 0.5 < both["k_err"] / (np.mean(errs) / np.sqrt(3)) < 1.6
    free = mn.fit(nights, P, start, free_midtimes=True)
    for tc, e, c in zip(free["midtimes"], free["midtimes_err"], (0, 7, 15), strict=True):
        assert tc == pytest.approx(T0 + c * P, abs=4 * e)
