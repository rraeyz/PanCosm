"""EXO-5: the inference engine — known targets, coverage, resuming, the diagnostics."""

import numpy as np
import pytest

from astrowb.core.inference import diagnostics, mcmc, priors
from astrowb.core.inference.problem import Problem
from astrowb.core.inference.results import Posterior, rounded


def gaussian_problem(d=20, seed=0):
    rng = np.random.default_rng(seed)
    a = rng.normal(size=(d, d))
    cov = a @ a.T / d + 0.1 * np.eye(d)
    mu = rng.normal(size=d)
    icov = np.linalg.inv(cov)
    names = [f"p{i}" for i in range(d)]

    def ll(v):
        x = np.stack([v[n] for n in names], -1) - mu
        return -0.5 * np.einsum("...i,ij,...j->...", x, icov, x)

    sd = np.sqrt(np.diag(cov))
    return Problem({n: (priors.Uniform(-50, 50), 0.0, s) for n, s in zip(names, sd, strict=True)}, ll,
                   vectorized=True), mu, cov  # fmt: skip


@pytest.mark.slow
def test_a_correlated_20_dimensional_gaussian_with_the_default_stopping_rule():
    problem, mu, cov = gaussian_problem()
    post = mcmc.run(problem, seed=1, max_steps=40000)
    assert post.converged
    # within 4 Monte Carlo errors of the run's own effective size (at ESS 1000 a mean is itself only good to 3 % of
    # σ, so "within 3 %" is asked of the covariance, which this run's larger ESS meets)
    ess = np.array([b for _r, b, _t in post.diagnostics.values()])
    sd = np.sqrt(np.diag(cov))
    assert np.all(np.abs(post.samples.mean(axis=0) - mu) / sd < 4 / np.sqrt(ess))
    got = np.cov(post.samples, rowvar=False)
    assert np.max(np.abs(got - cov) / np.sqrt(np.outer(np.diag(cov), np.diag(cov)))) < 0.03


@pytest.mark.slow
def test_the_banana():
    def ll(v):  # Rosenbrock's banana, scaled: x ~ N(1, 1), y | x ~ N(x², 0.1²)
        return -0.5 * (v["x"] - 1) ** 2 - 0.5 * ((v["y"] - v["x"] ** 2) / 0.1) ** 2

    p = Problem({"x": (priors.Uniform(-10, 10), 1.0, 1.0), "y": (priors.Uniform(-10, 50), 1.0, 1.0)}, ll,
                vectorized=True)  # fmt: skip
    post = mcmc.run(p, seed=3, max_steps=40000)
    assert post.converged
    x, y = post.samples.T
    assert np.mean(x) == pytest.approx(1.0, abs=0.08) and np.std(x) == pytest.approx(1.0, rel=0.06)
    assert np.mean(y) == pytest.approx(2.0, abs=0.15)  # E[x²] = 1 + 1


@pytest.mark.slow
def test_68_percent_intervals_cover_the_truth():
    x = np.linspace(0, 1, 20)
    hits = 0
    for k in range(150):
        y = 1.0 + 2.0 * x + np.random.default_rng(100 + k).normal(0, 0.1, 20)

        def ll(v, y=y):
            return -0.5 * np.sum((y - v["a"][:, None] - v["b"][:, None] * x) ** 2, axis=1) / 0.01

        p = Problem({"a": (priors.Uniform(-10, 10), 1.0, 0.05), "b": (priors.Uniform(-10, 10), 2.0, 0.08)}, ll,
                    vectorized=True)  # fmt: skip
        s = mcmc.run(p, seed=k, ess_min=400).summary()
        for name, truth in (("a", 1.0), ("b", 2.0)):
            hits += s[name]["median"] - s[name]["minus"] <= truth <= s[name]["median"] + s[name]["plus"]
    assert 0.62 <= hits / 300 <= 0.74  # 300 intervals: 68 % ± 2.2 σ


def test_a_resumed_run_gives_the_same_chain(tmp_path):
    problem, _mu, _cov = gaussian_problem(d=4)
    whole = mcmc.run(problem, seed=7, max_steps=1200, ess_min=1e9)
    path = str(tmp_path / "run.npz")
    mcmc.run(problem, seed=7, max_steps=600, ess_min=1e9, checkpoint=path)
    resumed = mcmc.run(problem, seed=7, max_steps=1200, ess_min=1e9, checkpoint=path)
    assert np.array_equal(whole.chains, resumed.chains) and not resumed.converged


def test_a_not_vectorised_likelihood_in_threads_and_failures_outside_the_model():
    def ll(v):
        if v["s"] <= 0:
            raise ValueError("no")
        return -0.5 * (v["m"] / v["s"]) ** 2 - np.log(v["s"]) - 0.5 * ((v["s"] - 1) / 0.2) ** 2

    p = Problem({"m": (priors.Gaussian(0, 10), 0.0, 1.0), "s": (priors.Uniform(-1, 5), 1.0, 0.2),
                 "k": (priors.Fixed(3.0), 3.0, 0.0)}, ll)  # fmt: skip
    assert p.dim == 2 and p.values([1.0, 2.0])["k"] == 3.0 and p([0.0, -0.5]) == -np.inf
    post = mcmc.run(p, seed=2, max_steps=3000, ess_min=200, workers=3)
    assert post.converged and np.all(post.samples[:, 1] > 0)


def test_priors():
    rng = np.random.default_rng(0)
    for prior in (priors.Uniform(1, 3), priors.LogUniform(1, 100), priors.Gaussian(2, 0.5),
                  priors.TruncatedGaussian(0, 1, 0, 2)):  # fmt: skip
        u = rng.random(20000)
        x = prior.transform(u)
        assert np.all(np.isfinite(prior.logpdf(x)))
        # the transform's density matches logpdf: compare a histogram with the density
        h, edges = np.histogram(x, bins=20, density=True)
        mid = 0.5 * (edges[1:] + edges[:-1])
        assert np.allclose(h, np.exp(prior.logpdf(mid)), rtol=0.15, atol=0.02)
        assert prior.describe()
    assert priors.Uniform(0, 1).logpdf(2.0) == -np.inf
    rho = priors.Derived("ρ★", lambda v: v["m"] / v["r"] ** 3, priors.Gaussian(1.0, 0.1))
    assert rho.logpdf({"m": 1.0, "r": 1.0}) == pytest.approx(priors.Gaussian(1.0, 0.1).logpdf(1.0))


def test_diagnostics_on_known_chains():
    rng = np.random.default_rng(5)
    iid = rng.normal(size=(4, 1000))
    assert diagnostics.rhat(iid) < 1.01
    assert 3000 < diagnostics.ess_bulk(iid) < 5000 and 2000 < diagnostics.ess_tail(iid) < 5500
    shifted = iid + np.array([0, 0, 0, 1.0])[:, None]
    assert diagnostics.rhat(shifted) > 1.1
    ar = np.zeros((4, 4000))  # AR(1) with ρ = 0.9: τ = 19, ESS ≈ 16000 / 19
    for t in range(1, 4000):
        ar[:, t] = 0.9 * ar[:, t - 1] + rng.normal(size=4)
    assert diagnostics.ess_bulk(ar) == pytest.approx(16000 / 19, rel=0.25)


def test_posterior_summary_rounding_and_storage(tmp_path):
    rng = np.random.default_rng(0)
    post = Posterior(["a", "b"], rng.normal([1, 5], [0.1, 2], size=(40000, 2)), np.zeros(40000))
    post.add_derived("c", lambda v: v["a"] * v["b"])
    s = post.summary()
    assert s["a"]["median"] == pytest.approx(1, abs=0.005) and s["b"]["plus"] == pytest.approx(2, rel=0.03)
    assert "c" in s and abs(post.correlation()[0, 1]) < 0.02
    assert rounded(1.23456, 0.0123, 0.0456) == ("1.235", "0.012", "0.046")
    post.save(tmp_path / "p.npz")
    for name in ("s.ecsv", "s.fits"):
        post.export(tmp_path / name)
        from astropy.table import Table

        t = Table.read(tmp_path / name)
        assert list(t["name"]) == ["a", "b", "c"] and t["median"][0] == pytest.approx(s["a"]["median"])
    back = Posterior.load(tmp_path / "p.npz")
    assert np.array_equal(back.samples, post.samples) and np.allclose(back.column("c"), post.column("c"))


def test_the_optimiser_finds_the_best_point_and_reports_both_modes():
    from astrowb.core.inference import optimise

    def ll(v):  # two separated peaks, the one at +3 higher
        a = -0.5 * ((v["x"] - 3) ** 2 + (v["y"] - 1) ** 2) / 0.04
        b = -0.5 * ((v["x"] + 3) ** 2 + (v["y"] + 1) ** 2) / 0.04 - 2.0
        return np.logaddexp(a, b)

    p = Problem({"x": (priors.Uniform(-10, 10), -3.0, 0.2), "y": (priors.Gaussian(0, 3), -1.0, 0.2)}, ll)
    x, lp = optimise.best(p)
    y = 1 / (1 + 0.04 / 9)  # the Gaussian prior on y pulls the peak in
    assert x == pytest.approx([3, y], abs=1e-5)
    found = optimise.modes(p, n_starts=32)
    assert len(found) == 2
    assert found[0][0] == pytest.approx([3, y], abs=1e-4) and found[1][0] == pytest.approx([-3, -y], abs=1e-4)
    assert found[0][1] - found[1][1] == pytest.approx(2.0, abs=1e-6)


def test_parallel_tempering_weighs_two_separated_modes():
    def ll(v):  # 30 % at (−3, −3), 70 % at (+3, +3), σ = 0.5: no chain crosses between them without tempering
        a = -0.5 * ((v["x"] + 3) ** 2 + (v["y"] + 3) ** 2) / 0.25 + np.log(0.3)
        b = -0.5 * ((v["x"] - 3) ** 2 + (v["y"] - 3) ** 2) / 0.25 + np.log(0.7)
        return np.logaddexp(a, b)

    p = Problem({"x": (priors.Uniform(-10, 10), 3.0, 0.5), "y": (priors.Uniform(-10, 10), 3.0, 0.5)}, ll,
                vectorized=True)  # fmt: skip
    cold = mcmc.run(p, seed=4, max_steps=3000, ess_min=1e9)
    assert np.mean(cold.samples[:, 0] < 0) < 0.02  # stuck in the mode it started in
    hot = mcmc.run(p, seed=4, max_steps=40000, temperatures=6, t_max=200)
    assert hot.converged
    assert np.mean(hot.samples[:, 0] < 0) == pytest.approx(0.3, rel=0.1)
