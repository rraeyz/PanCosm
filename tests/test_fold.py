"""PER-5: the period refined with an honest error, an eclipsing binary's minima measured, P or 2P decided."""

import numpy as np

from astrowb.timeseries import fold, methods

P, T0 = 0.3612, 0.11


def nightly(rng, n=600, nights=20):
    return np.sort(rng.integers(0, nights, n) + 0.3 + rng.uniform(0, 0.35, n))


def w_uma(t, d1=0.3, d2=0.24):
    ph = ((t - T0) / P) % 1
    return 1 - d1 * np.exp(-0.5 * (((ph + 0.5) % 1 - 0.5) / 0.1) ** 2) - d2 * np.exp(-0.5 * ((ph - 0.5) / 0.1) ** 2)


def algol(t):  # an eccentric orbit: the secondary at phase 0.53
    ph = ((t - T0) / P) % 1
    return (
        1 - 0.4 * np.exp(-0.5 * (((ph + 0.5) % 1 - 0.5) / 0.03) ** 2) - 0.1 * np.exp(-0.5 * ((ph - 0.53) / 0.03) ** 2)
    )


def test_the_refined_period_is_within_its_error():
    pulls = []
    for seed in range(20):
        rng = np.random.default_rng(seed)
        t = nightly(rng)
        period, error = fold.refine(t, w_uma(t) + rng.normal(0, 0.01, t.size), P * 1.0003)
        pulls.append((period - P) / error)
    assert np.mean(np.abs(pulls) < 1) > 0.5 and np.max(np.abs(pulls)) < 4 and 0.6 < np.std(pulls) < 1.5


def test_a_w_uma_found_at_half_its_period_is_given_its_orbital_period():
    rng = np.random.default_rng(1)
    t = nightly(rng)
    y = w_uma(t) + rng.normal(0, 0.01, t.size)
    half = methods.gls(t, y, p_min=0.1, p_max=3)[2]
    assert abs(half / (P / 2) - 1) < 1e-3  # a sinusoid fit sees two equal-looking dips per orbit
    which = fold.p_or_2p(t, y, half, T0)
    assert which["z"] > 3 and abs(which["period"] / P - 1) < 1e-3
    equal = fold.p_or_2p(t, w_uma(t, 0.27, 0.27) + rng.normal(0, 0.01, t.size), P / 2, T0)
    assert equal["z"] < 3 and equal["period"] == P / 2  # equal minima: nothing tells the halves apart


def test_the_minima_of_an_eccentric_algol():
    rng = np.random.default_rng(2)
    t = nightly(rng)
    e = fold.eclipses(t, algol(t) + rng.normal(0, 0.005, t.size), P, T0)
    assert abs(e["primary_depth"] - 0.4) < 0.02 and abs(e["secondary_depth"] - 0.1) < 0.02
    assert abs(e["primary_width"] - 2.355 * 0.03) < 0.01 and abs(e["phase_difference"] - 0.53) < 0.01
    assert abs(e["ecosw"] - np.pi / 2 * 0.03) < 0.02
    phase, med, err = fold.binned(t, algol(t), P, T0)
    assert len(phase) == 50 and np.nanmin(med) < 0.65
