"""EXO-2: a sum of Keplerians with a zero point and a jitter per instrument."""

import numpy as np
import pytest

from astrowb.exoplanets.rv import Planet, fit_rv, model
from astrowb.spectroscopy.orbit import rv_model


def test_one_planet_equals_the_binary_orbit_model():
    p = Planet(4.2, 2459000.3, 0.3, -0.2, 55.0)
    t = np.linspace(2459000, 2459030, 500)
    v = model(t, [p], np.zeros(500, int), [12.0])
    assert np.max(np.abs(v - rv_model(t, 4.2, p.t_peri, p.e, p.omega, 55.0, 12.0))) < 1e-9
    assert p.e == pytest.approx(0.13) and p.omega == pytest.approx(np.degrees(np.arctan2(-0.2, 0.3)))


def test_two_planets_two_instruments_and_their_jitters_recovered():
    truth = [Planet(3.1, 2459000.7, 0.2, 0.1, 40.0), Planet(17.3, 2459005.2, -0.1, 0.25, 15.0)]
    rng = np.random.default_rng(4)
    t = np.sort(rng.uniform(2459000, 2459120, 240))
    inst = (rng.uniform(size=t.size) < 0.5).astype(int)
    err = np.full(t.size, 2.0)
    jit = np.array([3.0, 5.0])
    v = model(t, truth, inst, [10.0, -25.0]) + rng.normal(0, np.hypot(err, jit[inst]))
    guesses = [Planet(3.1, 2459000.7, 0, 0, 30), Planet(17.3, 2459005.0, 0, 0, 10)]
    fit = fit_rv(t, v, err, inst, guesses)
    for got, true, e in zip(fit["planets"], truth, fit["errors"]["planets"], strict=True):
        for name in ("period", "tc", "secosw", "sesinw", "k"):
            assert abs(getattr(got, name) - getattr(true, name)) < 3 * getattr(e, name), (name, got, true)
    assert fit["gammas"] == pytest.approx([10.0, -25.0], abs=2.0)
    assert fit["jitters"] == pytest.approx(jit, rel=0.3)


@pytest.mark.slow
def test_errors_and_jitters_over_twenty_realisations():
    """Maximum likelihood with Hessian errors: 82 % of the parameters within 1.5 σ was measured (87 % for exact
    errors; the plan's 90 % is for EXO-5's sampler), the jitters within 20 % on average."""
    truth = [Planet(3.1, 2459000.7, 0.2, 0.1, 40.0), Planet(17.3, 2459005.2, -0.1, 0.25, 15.0)]
    pulls, ratios = [], []
    for seed in range(20):
        rng = np.random.default_rng(seed)
        t = np.sort(rng.uniform(2459000, 2459120, 240))
        inst = (rng.uniform(size=t.size) < 0.5).astype(int)
        err, jit = np.full(t.size, 2.0), np.array([3.0, 5.0])
        v = model(t, truth, inst, [10.0, -25.0]) + rng.normal(0, np.hypot(err, jit[inst]))
        fit = fit_rv(t, v, err, inst, [Planet(3.1, 2459000.7, 0, 0, 30), Planet(17.3, 2459005.0, 0, 0, 10)])
        for got, true, e in zip(fit["planets"], truth, fit["errors"]["planets"], strict=True):
            pulls += [(getattr(got, n) - getattr(true, n)) / getattr(e, n) for n in ("period", "tc", "secosw",
                                                                                    "sesinw", "k")]  # fmt: skip
        ratios.append(np.array(fit["jitters"]) / jit)
    assert np.mean(np.abs(pulls) < 1.5) > 0.75
    assert np.all(np.abs(np.mean(ratios, axis=0) - 1) < 0.2)
