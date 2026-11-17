"""UI-16.6: per-parameter priors (uniform / log-uniform) of the binary-star MCMC."""

import numpy as np
import pytest

from astrowb.core.inference import mcmc as engine
from astrowb.models import fit

TRUTH = {"period": 1.7, "t0": 0.25, "r_sum": 0.3, "k": 0.6, "incl": 86.0, "j": 0.5, "ecosw": 0.0, "esinw": 0.0,
         "l3": 0.0}  # fmt: skip


@pytest.fixture(scope="module")
def synthetic():
    rng = np.random.default_rng(3)
    t = np.sort(rng.uniform(0, 6, 200))
    f = fit.model(t, TRUTH, (0.4, 0.2), (0.4, 0.2)) + rng.normal(0, 0.003, len(t))
    err = np.full(len(t), 0.003)
    return t, f, err, fit.fit_light_curve(t, f, err, TRUTH | {"exposure": 0.0}, ["k", "incl"])


def test_log_uniform_follows_the_prior_where_the_data_say_nothing():
    def flat(x):
        return 0.0  # no likelihood: the posterior is the prior

    args = (flat, np.array([10.0]), np.array([5.0]), ["x"], [1.0], [100.0], 300)
    uni = engine.around(*args).samples[:, 0]
    log = engine.around(*args, log_uniform=["x"]).samples[:, 0]
    assert np.median(uni) > 35 and 5 < np.median(log) < 20  # the geometric middle of 1 and 100 is 10


def test_default_priors_leave_the_mcmc_unchanged_and_log_uniform_runs(synthetic):
    t, f, err, r = synthetic
    base = fit.mcmc(t, f, err, r, ["k"], steps=100)
    same = fit.mcmc(t, f, err, r, ["k"], steps=100, priors={"k": "uniform"})
    assert same["samples"] == base["samples"]
    logu = fit.mcmc(t, f, err, r, ["k"], steps=100, priors={"k": "log-uniform"})
    assert np.isfinite(logu["params"]["k"][0])


@pytest.mark.parametrize("bounds", [None, {"j": (-1.0, 5.0)}, {"j": (0.1, np.inf)}])
def test_a_log_uniform_prior_needs_finite_limits_above_zero(bounds):
    with pytest.raises(ValueError, match="finite limits above zero"):
        fit.log_uniform_names({"j": "log-uniform"}, bounds)  # j: the default lower limit is 0
    with pytest.raises(ValueError, match="unknown prior"):
        fit.log_uniform_names({"k": "gaussian"}, None)
    assert fit.log_uniform_names({"k": "log-uniform", "j": "uniform"}, None) == ["k"]
