"""Uncertainties of a fitted system (plans/models.md MOD-14), three ways side by side: Monte Carlo (the fitted model
plus noise of each set's scatter, refitted), residual permutation ("prayer bead": the residuals shifted cyclically
through each set, refitted — keeps red noise), and the shared inference engine's MCMC on the parameters with their
limits and priors. Each returns {name: standard deviation} (MCMC also the posterior)."""

import numpy as np

from . import fitting


def _fitted(system, model):
    out = []
    for d in system.data:
        vals = {k: p.value for k, p in system.params.items()}
        out.append(fitting._linear(d, np.asarray(model(vals, d), float))[0])
    return out


def _refit_spread(system, model, make_sets, free, optimiser):
    start = {k: p.value for k, p in system.params.items()}
    originals = [d.value for d in system.data]
    rows = []
    try:
        for values in make_sets:
            for d, v in zip(system.data, values, strict=True):
                d.value = v
            for k, v in start.items():
                system.params[k].value = v
            system.apply()
            rows.append([fitting.fit(system, model, optimiser, free).values[k] for k in free])
    finally:
        for d, v in zip(system.data, originals, strict=True):
            d.value = v
        for k, v in start.items():
            system.params[k].value = v
        system.apply()
    return dict(zip(free, np.std(np.array(rows), axis=0, ddof=1), strict=True))


def monte_carlo(system, model, n=50, seed=1, optimiser="lm"):
    free = system.free()
    fitted = _fitted(system, model)
    rng = np.random.default_rng(seed)
    scatter = [np.std(np.asarray(d.value) - f) for d, f in zip(system.data, fitted, strict=True)]
    sets = ([f + rng.normal(0, s, f.size) for f, s in zip(fitted, scatter, strict=True)] for _ in range(n))
    return _refit_spread(system, model, sets, free, optimiser)


def prayer_bead(system, model, n=50, optimiser="lm"):
    free = system.free()
    fitted = _fitted(system, model)
    resid = [np.asarray(d.value) - f for d, f in zip(system.data, fitted, strict=True)]
    shifts = np.linspace(0, 1, n, endpoint=False)
    sets = ([f + np.roll(r, int(s * r.size)) for f, r in zip(fitted, resid, strict=True)] for s in shifts)
    return _refit_spread(system, model, sets, free, optimiser)


def mcmc(system, model, steps=2000, seed=1, weights="errors"):
    """(standard deviations, Posterior) from the shared engine; flat priors within the limits, Gaussian ones as
    the parameters state."""
    from ..core.inference import mcmc as engine
    from ..core.inference.priors import Flat, Gaussian
    from ..core.inference.problem import Problem

    free = system.free()
    sigmas = fitting._sigmas(system, model, weights)
    row = fitting.fit(system, model, "lm", free, weights)
    params = {}
    for k in free:
        p = system.params[k]
        prior = Gaussian(p.prior[1], p.prior[2]) if p.prior and p.prior[0] == "gaussian" else Flat(p.lower, p.upper)
        params[k] = (prior, p.value, row.errors.get(k) or 1e-3)

    def ll(vals):
        x = [vals[k] for k in free]
        res = fitting.residuals(system, model, sigmas, free, x)
        return -0.5 * float(res @ res)

    post = engine.run(Problem(params, ll), seed=seed, max_steps=steps, check_every=100)
    return dict(zip(free, np.std(post.samples, axis=0), strict=True)), post
