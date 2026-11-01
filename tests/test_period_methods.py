"""PER-3: the methods advised for each kind of light curve recover its period from nightly, gappy data."""

import numpy as np
import pytest

from astrowb.timeseries import methods, period

P = 0.6123


def nightly(rng, n=250, nights=30):
    return np.sort(rng.integers(0, nights, n) + 0.3 + rng.uniform(0, 0.3, n))  # 7 hours a night


def sine(t):
    return np.sin(2 * np.pi * t / P)


def sawtooth(t):  # RR Lyrae-like: a fast rise, a slow decline
    ph = (t / P) % 1
    return np.where(ph < 0.15, ph / 0.15, 1 - (ph - 0.15) / 0.85)


def algol(t):  # a 40 % primary and a 10 % secondary, each 3 % of the cycle wide
    ph = (t / P + 0.5) % 1 - 0.5
    sec = (ph + 1) % 1 - 0.5
    return 1 - 0.4 * np.exp(-0.5 * (ph / 0.03) ** 2) - 0.1 * np.exp(-0.5 * (sec / 0.03) ** 2)


ADVISED = {  # the methods the guide advises for each shape (conditional entropy picks half an Algol's period)
    "sine": (sine, 0.3, ("gls", "aovmh", "conditional_entropy", "pdm")),
    "sawtooth": (sawtooth, 0.1, ("gls", "aovmh", "conditional_entropy", "pdm")),
    "algol": (algol, 0.01, ("aovmh", "string_length", "pdm")),
}


@pytest.mark.slow
@pytest.mark.parametrize("shape", list(ADVISED))
def test_the_advised_methods_find_the_period(shape):
    curve, noise, advised = ADVISED[shape]
    for name in advised:
        func = getattr(methods, name, None) or getattr(period, name)
        found = 0
        for seed in range(20):
            rng = np.random.default_rng(seed)
            t = nightly(rng)
            best = func(t, curve(t) + rng.normal(0, noise, t.size), p_min=0.2, p_max=5)[2]
            found += abs(best / P - 1) < 0.005
        assert found >= 19, (shape, name, found)  # ≥ 95 %


def test_statistics_from_their_papers_on_small_data():
    t = np.linspace(0, 10, 200)
    y = np.sin(2 * np.pi * t / 2.5)
    tt, yy, w = methods._prepare(t, y)
    f = np.array([1 / 2.5, 1 / 3.7])
    sl = methods._sl_power(tt, yy, f)
    assert sl[0] > 0.99 and sl[1] < 0.5  # Lafler–Kinman: neighbours in phase alike only at the period
    ce = methods._ce_power(tt, yy, f)
    assert ce[0] > ce[1]
    aov = methods._aovmh_power(tt, yy, w, f, 2)
    assert aov[0] > 1e6 and aov[1] < 100  # a noise-free sine: the residual vanishes at its period


def test_the_period_step_runs_every_method():
    from types import SimpleNamespace

    from astrowb.engine.steps import execute

    ctx = SimpleNamespace(progress=lambda *a: None, check=lambda: None)
    rng = np.random.default_rng(1)
    t = nightly(rng)
    y = sawtooth(t) + rng.normal(0, 0.05, t.size)
    for method in ("gls", "aovmh", "conditional_entropy", "string_length"):
        out = execute("timeseries.period", {"time": list(t), "flux": list(y)}, {"method": method, "p_max": 5.0}, ctx)
        assert abs(out["best"] / P - 1) < 0.005, method
