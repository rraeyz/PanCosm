"""OC-6: the light-travel-time effect found without start values, with a parabola, two orbits, derived values."""

import numpy as np
import pytest

from astrowb.timeseries import ltte

P, T0 = 0.4, 2450000.0
ORBIT = {"P3": 3000.0, "T3": T0 + 700, "e": 0.4, "omega": 120.0, "A": 0.008}


def minima(seed, orbits=(ORBIT,), q=0.0, n=300, sigma=0.0004, cycles=2.3):
    rng = np.random.default_rng(seed)
    e = np.sort(rng.choice(np.arange(int(cycles * ORBIT["P3"] / P)), n, replace=False)).astype(float)
    t = T0 + P * e + q * e**2
    for o in orbits:
        t = t + o["A"] * ltte.tau(t, o["P3"], o["T3"], o["e"], o["omega"])
    return t + rng.normal(0, sigma, n), e, np.full(n, sigma)


def _close(o, truth, k):
    keys = ("P3", "e", "omega", "A")
    return {key: abs(o[key] - truth[key]) < k * o[key + "_err"] for key in keys}


@pytest.mark.slow
def test_an_eccentric_orbit_is_found_without_start_values():
    inside = {key: 0 for key in ("P3", "e", "omega", "A")}
    for seed in range(30):
        f = ltte.search(*minima(seed), seed=seed)
        o = f["orbits"][0]
        assert all(_close(o, ORBIT, 4).values()), seed  # never the wrong valley
        for key, ok in _close(o, ORBIT, 1.5).items():
            inside[key] += ok
    assert min(inside.values()) >= 22  # 1.5 σ holds 87 %: at least 22 of 30


def test_with_a_parabola_and_the_derived_values():
    f = ltte.search(*minima(3, q=3e-11), order=2, seed=3)
    o = f["orbits"][0]
    assert all(_close(o, ORBIT, 4).values())
    assert f["Q"] == pytest.approx(3e-11, abs=4 * f["Q_err"]) and f["chi2r"] < 1.3
    d = ltte.derived(o, m12=2.0, span=2.3 * ORBIT["P3"])
    assert d["a12_sini_au"] == pytest.approx(0.008 * ltte.AU_PER_LIGHT_DAY, rel=0.02)
    assert d["m3_min"] < d["m3_60"] < d["m3_30"] and not d["coverage_warning"]
    m = d["m3_min"]
    assert m**3 / (2.0 + m) ** 2 == pytest.approx(d["f_m3"], rel=1e-8)
    assert ltte.derived(o, span=1000.0)["coverage_warning"]
    ok, ratio, limit = ltte.stable(0.4, 3000.0, 0.4, 2.0, 0.65)
    assert ok and ratio > limit
    assert not ltte.stable(10.0, 40.0, 0.6, 2.0, 1.0)[0]


@pytest.mark.slow
def test_two_orbits():
    second = {"P3": 800.0, "T3": T0 + 100, "e": 0.1, "omega": 40.0, "A": 0.003}
    f = ltte.search(*minima(5, orbits=(ORBIT, second), n=500, sigma=0.0002), n_orbits=2, seed=5)
    short, long_ = f["orbits"]
    assert all(_close(long_, ORBIT, 4).values()) and all(_close(short, second, 4).values())


def test_the_posterior_of_the_fit():
    t, e, s = minima(7, n=150)
    f = ltte.search(t, e, s, seed=7)
    post = ltte.posterior(t, e, s, f, steps=3000)
    o = f["orbits"][0]
    med, lo, hi = post["params"]["e_1"]
    assert med == pytest.approx(o["e"], abs=0.5 * o["e_err"]) and 0.5 < (lo + hi) / 2 / o["e_err"] < 2
    assert set(post["params"]) >= {"T0", "P", "P3_1", "A_1", "omega_1"}


def test_the_residual_periodogram_justifies_the_orbit():
    from astrowb.timeseries import ephemeris_models as em

    t, e, s = minima(2, n=200)
    lin = em.fit(t, e, s, 1)
    _p, _power, best, fap = ltte.residual_periodogram(t, lin["residuals"], s)
    assert best == pytest.approx(ORBIT["P3"], rel=0.1) and fap < 1e-10
    noise = np.random.default_rng(0).normal(0, 0.0004, t.size)
    assert ltte.residual_periodogram(t, noise, s)[3] > 0.01
