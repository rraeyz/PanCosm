"""OC-8: coverage of the LTTE and apsidal errors, the bootstrap, the jitter, correlations."""

import numpy as np
import pytest

from astrowb.timeseries import apsidal as ap
from astrowb.timeseries import ltte
from astrowb.timeseries import oc_uncertainty as ou

P, T0 = 0.4, 2450000.0
ORBIT = {"P3": 3000.0, "T3": T0 + 700, "e": 0.4, "omega": 120.0, "A": 0.008}


def ltte_minima(seed, n=200):
    rng = np.random.default_rng(seed)
    e = np.sort(rng.choice(np.arange(int(2.3 * ORBIT["P3"] / P)), n, replace=False)).astype(float)
    t = T0 + P * e
    t = t + ORBIT["A"] * ltte.tau(t, ORBIT["P3"], ORBIT["T3"], ORBIT["e"], ORBIT["omega"])
    return t + rng.normal(0, 0.0004, n), e, np.full(n, 0.0004)


def truth_start(t):
    tm = float(np.median(t))
    w = np.radians(ORBIT["omega"])
    return [ORBIT["P3"], ((ORBIT["T3"] - tm) / ORBIT["P3"]) % 1, np.sqrt(0.4) * np.cos(w), np.sqrt(0.4) * np.sin(w)]


@pytest.mark.slow
def test_ltte_intervals_cover_the_truth():
    inside = dict.fromkeys(("P3", "e", "omega", "A"), 0)
    for seed in range(300):
        t, e, s = ltte_minima(seed)
        o = ltte.fit(t, e, s, truth_start(t))["orbits"][0]
        for key in inside:
            inside[key] += abs(o[key] - ORBIT[key]) < o[key + "_err"]
    assert all(0.62 <= v / 300 <= 0.74 for v in inside.values()), inside


@pytest.mark.slow
def test_apsidal_intervals_cover_the_truth():
    ps, rate = 3.0, 360 * 3.0 / (80 * 365.25)
    truth = {"Ps": ps, "e": 0.25, "omega0": 70.0, "d_omega": rate}
    inside = dict.fromkeys(truth, 0)
    for seed in range(300):
        rng = np.random.default_rng(seed)
        cyc = np.sort(rng.choice(np.arange(int(40 * 365.25 / ps)), 80, replace=False)).astype(float)
        ep = np.concatenate([cyc[:40], cyc[40:] + 0.5])
        t = ap.times(ep, T0, ps, 0.25, 70.0, rate, 85.0) + rng.normal(0, 0.0003, ep.size)
        f = ap.fit(ep, t, np.full(ep.size, 0.0003), 85.0, start=(T0, ps, 0.25, 70.0, rate))
        for key in inside:
            inside[key] += abs(f[key] - truth[key]) < f[key + "_err"]
    assert all(0.62 <= v / 300 <= 0.74 for v in inside.values()), inside


def test_bootstrap_jitter_and_correlations():
    t, e, s = ltte_minima(1)
    start = truth_start(t)
    best = ltte.fit(t, e, s, start)
    model = t - best["residuals"]

    def refit(data):
        o = ltte.fit(data, e, s, start)["orbits"][0]
        return {k: o[k] for k in ("P3", "e", "A")}

    spread, sd = ou.bootstrap(refit, model, t, n=60)
    o = best["orbits"][0]
    for key in ("P3", "e", "A"):
        assert sd[key] == pytest.approx(o[key + "_err"], rel=0.4)
    # errors stated 2× too small: the jitter brings χ²ᵣ back to 1
    small = s / 2
    fitted, jit = ou.with_jitter(lambda err: ltte.fit(t, e, err, start), lambda r: r["residuals"], small, 8)
    assert jit == pytest.approx(np.sqrt(0.0004**2 - 0.0002**2), rel=0.15)
    assert ou.jitter(best["residuals"], s * 3, 8) == 0.0
    rho, tied = ou.correlation(np.array([[1, 0.95], [0.95, 1]]), ["a", "b"])
    assert tied == [("a", "b", 0.95)] and rho[0, 1] == 0.95
