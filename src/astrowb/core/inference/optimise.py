"""The best fit, the start of every sampler (EXO-5 item 3): bounded differential evolution over the priors' ranges,
polished by Nelder–Mead; with n_starts > 1 local searches from scattered points find the separate modes, which
are reported (not hidden) with their log-probabilities."""

import numpy as np
from scipy.optimize import differential_evolution, minimize

from . import priors


def bounds(problem, width=5.0):
    """The search box from the priors: a uniform's limits; a Gaussian's mean ± width σ (cut by truncation)."""
    out = []
    for p, start, scale in zip(problem.priors, problem.start, problem.scale, strict=True):
        if isinstance(p, priors.Uniform):
            out.append((p.lo, p.hi))
        elif isinstance(p, priors.Gaussian):
            lo, hi = p.mu - width * p.sigma, p.mu + width * p.sigma
            if isinstance(p, priors.TruncatedGaussian):
                lo, hi = max(lo, p.lo), min(hi, p.hi)
            out.append((lo, hi))
        else:
            out.append((start - width * scale, start + width * scale))
    return out


def _negative(problem):
    def f(theta):
        lp = problem(np.asarray(theta, float))
        return 1e300 if not np.isfinite(lp) else -lp

    return f


def best(problem, seed=1, polish=True, maxiter=1000):
    """(θ, log-probability) of the highest point found."""
    f = _negative(problem)
    got = differential_evolution(f, bounds(problem), seed=seed, maxiter=maxiter, tol=1e-10, polish=False,
                                 init="sobol", x0=np.clip(problem.start, *np.array(bounds(problem)).T))  # fmt: skip
    x = got.x
    if polish:
        x = _polish(f, x, problem.scale)
    return x, -f(x)


def _polish(f, x, scale):
    for _ in range(3):  # restarts: Nelder–Mead stalls on long valleys
        options = {"xatol": 1e-10, "fatol": 1e-12, "maxfev": 20000, "initial_simplex": _simplex(x, scale)}
        got = minimize(f, x, method="Nelder-Mead", options=options)
        if np.allclose(got.x, x, rtol=0, atol=1e-9):
            break
        x = got.x
    return x


def _simplex(x, scale):
    step = 0.1 * np.where(np.asarray(scale) > 0, scale, np.maximum(np.abs(x), 1.0) * 0.01)
    return np.vstack([x, x + np.diag(step)])


def modes(problem, n_starts=20, seed=1, separation=3.0):
    """The distinct local maxima from n_starts points spread over the box (Sobol), each polished: a list of
    (θ, log-probability), best first. Two maxima closer than separation × the scale in every parameter are one."""
    from scipy.stats import qmc

    box = np.array(bounds(problem))
    starts = qmc.scale(qmc.Sobol(problem.dim, seed=seed).random(n_starts), box[:, 0], box[:, 1])
    f = _negative(problem)
    found = []
    for s in starts:
        if not np.isfinite(problem(s)):
            continue
        x = _polish(f, s, problem.scale)
        lp = -f(x)
        if not np.isfinite(lp):
            continue
        same = [i for i, (y, _l) in enumerate(found) if np.all(np.abs(x - y) < separation * problem.scale)]
        if not same:
            found.append((x, lp))
        elif lp > found[same[0]][1]:
            found[same[0]] = (x, lp)
    return sorted(found, key=lambda m: -m[1])
