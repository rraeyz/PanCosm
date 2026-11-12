"""Uncertainties of the O−C models beyond the covariance (plans/oc.md OC-8): the bootstrap of residuals, a
jitter added in quadrature to errors that are too small, and the correlation table. The MCMC is the shared
inference engine's (core/inference; ltte.posterior, oc_models)."""

from concurrent.futures import ThreadPoolExecutor

import numpy as np
from scipy.optimize import brentq


def bootstrap(refit, model, observed, n=200, seed=1, workers=4):
    """Parameter spreads from n data sets made of the model plus the residuals drawn with replacement, each fitted
    again: refit(data) → dict of numbers. Returns {name: (median, minus, plus)} (16th / 84th percentiles) and the
    standard deviations."""
    model, observed = np.asarray(model, float), np.asarray(observed, float)
    resid = observed - model
    rng = np.random.default_rng(seed)
    sets = [model + rng.choice(resid, resid.size, replace=True) for _ in range(n)]
    with ThreadPoolExecutor(workers) as pool:
        rows = list(pool.map(refit, sets))
    out, sd = {}, {}
    for key in rows[0]:
        v = np.array([r[key] for r in rows], float)
        q = np.percentile(v, [16, 50, 84])
        out[key] = (float(q[1]), float(q[1] - q[0]), float(q[2] - q[1]))
        sd[key] = float(np.std(v, ddof=1))
    return out, sd


def jitter(residuals, errors, n_params):
    """The jitter s added in quadrature (σ² = err² + s²) that makes the reduced χ² of the residuals 1, or 0 when it
    is already below 1."""
    r, e = np.asarray(residuals, float), np.asarray(errors, float)
    dof = max(r.size - n_params, 1)

    def excess(s):
        return np.sum(r * r / (e * e + s * s)) / dof - 1

    if excess(0.0) <= 0:
        return 0.0
    return float(brentq(excess, 0.0, 10 * np.std(r) + np.max(np.abs(r))))


def with_jitter(fit, residuals_of, errors, n_params, rounds=10):
    """Fit with the errors inflated by a jitter fitted with the model: fit(errors) → result, residuals_of(result)
    → residuals; repeated until the jitter settles. Returns (result, jitter)."""
    e = np.asarray(errors, float)
    s = 0.0
    for _ in range(rounds):
        result = fit(np.sqrt(e * e + s * s))
        new = jitter(residuals_of(result), e, n_params)
        if abs(new - s) <= 1e-3 * max(new, 1e-12):
            return result, new
        s = new
    return result, s


def correlation(cov, names):
    """The correlation matrix and the pairs with |ρ| > 0.9 (strongly tied: say so next to the errors)."""
    cov = np.asarray(cov, float)
    sd = np.sqrt(np.clip(np.diag(cov), 1e-300, None))
    rho = cov / np.outer(sd, sd)
    tied = [(names[i], names[j], float(rho[i, j])) for i in range(len(names)) for j in range(i + 1, len(names))
            if abs(rho[i, j]) > 0.9]  # fmt: skip
    return rho, tied
