"""VAL-7: coverage of the ephemeris, frequency and apsidal errors."""

import numpy as np

from astrowb.timeseries import apsidal as ap
from astrowb.timeseries import ephemeris_models as em
from astrowb.timeseries import frequency as fq

from .harness import assert_honest, run


def test_quadratic_ephemeris():
    def simulate(seed):
        rng = np.random.default_rng(seed)
        e = np.sort(rng.choice(np.arange(-10000, 10000), 100, replace=False)).astype(float)
        return e, 2455000.0 + 0.4 * e + 2e-10 * e * e + rng.normal(0, 4e-4, e.size)

    def fit(data):
        e, t = data
        f = em.fit(t, e, np.full(e.size, 4e-4), 2)
        return {"P": (f["coef"][1], f["err"][1]), "Q": (f["coef"][2], f["err"][2])}

    assert_honest(run(simulate, fit, {"P": 0.4, "Q": 2e-10}))


def test_frequencies():
    def simulate(seed):
        rng = np.random.default_rng(seed)
        t = np.sort(rng.uniform(0, 30, 800))
        return t, 5 * np.sin(2 * np.pi * (7.3 * t + 0.1)) + 2 * np.sin(2 * np.pi * (11.9 * t + 0.6)) + rng.normal(
            0, 1, t.size)  # fmt: skip

    def fit(data):
        t, y = data
        terms, _ = fq.improve_all(t, y, [fq.term("F1", 7.3), fq.term("F2", 11.9)], linear_start=True, t_ref=0.0)
        return {f"f{i}": (v["freq"], v["freq_err"]) for i, v in enumerate(terms)} | {
            f"a{i}": (v["amp"], v["amp_err"]) for i, v in enumerate(terms)}  # fmt: skip

    assert_honest(run(simulate, fit, {"f0": 7.3, "f1": 11.9, "a0": 5.0, "a1": 2.0}))


def test_apsidal_motion():
    ps, rate = 3.0, 360 * 3.0 / (80 * 365.25)

    def simulate(seed):
        rng = np.random.default_rng(seed)
        cyc = np.sort(rng.choice(np.arange(int(40 * 365.25 / ps)), 80, replace=False)).astype(float)
        ep = np.concatenate([cyc[:40], cyc[40:] + 0.5])
        return ep, ap.times(ep, 2450000.0, ps, 0.25, 70.0, rate, 85.0) + rng.normal(0, 3e-4, ep.size)

    def fit(data):
        ep, t = data
        f = ap.fit(ep, t, np.full(ep.size, 3e-4), 85.0, start=(2450000.0, ps, 0.25, 70.0, rate))
        return {k: (f[k], f[k + "_err"]) for k in ("Ps", "e", "omega0", "d_omega")}

    assert_honest(run(simulate, fit, {"Ps": ps, "e": 0.25, "omega0": 70.0, "d_omega": rate}))
