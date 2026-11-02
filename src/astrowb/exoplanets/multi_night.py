"""Many transits of one planet (plans/exoplanets.md EXO-9): nights fitted together with a shared planet (k = Rp/R★,
a/R★, impact parameter b) and a baseline per night — the transit model times a polynomial in time, its
coefficients solved linearly inside every evaluation — on a linear ephemeris (T0, P) or with a free mid-time per
night (then the O−C machinery, OC-13, refines the ephemeris).

A night: (time, flux, error). Parameters returned with errors from the covariance (scaled by √χ²ᵣ when > 1).
"""

import numpy as np
from scipy.optimize import least_squares

from ..occult.model import transit


def _baseline(t, model, f, w, order):
    """The best polynomial baseline (multiplying the model) and its values."""
    x = t - t.mean()
    a = np.column_stack([model * x**k for k in range(order + 1)]) * w[:, None]
    coef, *_ = np.linalg.lstsq(a, f * w, rcond=None)
    return a @ coef / w


def fit(nights, period, start, law="quadratic", coeffs=(0.4, 0.2), order=1, free_midtimes=False, exposure=None):
    """start: {"t0", "k", "a_rs", "b"} (t0 a mid-time near the data). Returns {"k", "a_rs", "b", "inc", "t0",
    "period" (or "midtimes": one per night) with "_err" entries, "chi2r", "residuals" (per night)}."""
    data = [tuple(np.asarray(v, float) for v in night) for night in nights]
    n_cyc = [np.round((d[0].mean() - start["t0"]) / period) for d in data]
    names = ["k", "a_rs", "b"] + ([f"tc{i}" for i in range(len(data))] if free_midtimes else ["t0", "period"])
    t_ref = start["t0"]  # times are parameters relative to it: at 2.46e6 a finite-difference step is 0.04 d
    p0 = [start["k"], start["a_rs"], start["b"]]
    p0 += [c * period for c in n_cyc] if free_midtimes else [0.0, period]

    def resid(p, keep=False):
        k, a_rs, b = p[:3]
        if not (0 < k < 0.5 and a_rs > 1 and 0 <= b < 1 + k):
            return np.full(sum(len(d[0]) for d in data), 1e6)
        inc = np.degrees(np.arccos(b / a_rs))
        out = []
        for i, (t, f, e) in enumerate(data):
            tc, per = (p[3 + i], period) if free_midtimes else (p[3], p[4])
            m = transit(t - t_ref, per, tc, k, a_rs, inc, law, coeffs, exposure=exposure)
            out.append((f - _baseline(t, m, f, 1 / e, order)) / e)
        return out if keep else np.concatenate(out)

    p0 = np.array(p0, float)
    sols = []  # b and a/R★ trade off along a valley: started at several impact parameters, the best kept
    for b0 in dict.fromkeys([start["b"], 0.1, 0.5, 0.8]):
        trial = p0.copy()
        trial[2] = b0
        sols.append(least_squares(resid, trial, x_scale="jac", xtol=1e-12, ftol=1e-12))
    sol = min(sols, key=lambda r: r.cost)
    chi2r = float(np.sum(sol.fun**2) / max(sol.fun.size - len(p0), 1))
    cov = np.linalg.pinv(sol.jac.T @ sol.jac) * max(chi2r, 1.0)  # one night: T0 and P are one parameter
    err = np.sqrt(np.diag(cov))
    best = sol.x.copy()
    best[3 : len(best) if free_midtimes else 4] += t_ref
    out = {n: float(v) for n, v in zip(names, best, strict=True)}
    out |= {n + "_err": float(v) for n, v in zip(names, err, strict=True)}
    out["inc"] = float(np.degrees(np.arccos(out["b"] / out["a_rs"])))
    if free_midtimes:
        out["midtimes"] = [out[f"tc{i}"] for i in range(len(data))]
        out["midtimes_err"] = [out[f"tc{i}_err"] for i in range(len(data))]
    out["chi2r"], out["residuals"] = chi2r, resid(sol.x, keep=True)
    return out
