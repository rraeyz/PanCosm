"""The exact transit fitted in the Photometry window (plans/photometry.md PHO-26, the engine): flux =
baseline × transit(t; Tc, P, k, a/R★, b, u1, u2) × exp(Σ c_j z_j), the z_j the detrending series chosen in the
Light curve stage (airmass, sky, FWHM, x, y … scaled to unit spread), fitted by bounded least squares with
Gaussian priors where given; the transit is occult.model's (quadratic law, exposure integration).

Times are fitted relative to the first point (absolute JDs would make the finite-difference steps hours long).
"""

import numpy as np
from scipy.optimize import least_squares

from ..exoplanets.derived import density_from_a, t14, t23
from ..exoplanets.noise import beta_factor
from ..occult.model import transit

NAMES = ("tc", "k", "a_rs", "b", "u1", "u2", "baseline")
R_JUP, R_EARTH = 7.1492e7, 6.3781e6
R_SUN = 6.957e8


def _inc(a_rs, b):
    return float(np.degrees(np.arccos(np.clip(b / a_rs, -1, 1))))


def fit(t, flux, err, period, start, free=("tc", "k", "a_rs", "b", "baseline"), priors=None, detrend=None,
        exposure=None, mcmc_steps=0, ctx=None):  # fmt: skip
    """start: {"tc", "k", "a_rs", "b", "u1", "u2", "baseline"} (tc absolute); priors: {name: (centre, width)};
    detrend: {name: series}. Returns values, errors, derived quantities and fit statistics; with mcmc_steps, "mcmc":
    {name: (median, minus, plus)} of the posterior around the least-squares answer (core.inference, flat priors in
    the bounds, the Gaussian priors kept; the errors as given — scale them first when they are too small)."""
    t, f, e = (np.asarray(v, float) for v in (t, flux, err))
    t0 = float(t[0])
    x = t - t0
    vals = {k: float(v) for k, v in start.items()} | {"baseline": float(start.get("baseline", np.median(f)))}
    vals.setdefault("u1", 0.4)
    vals.setdefault("u2", 0.2)
    vals["tc"] -= t0
    names = [n for n in NAMES if n in free]
    z = {k: (np.asarray(v, float) - np.mean(v)) / (np.std(v) or 1.0) for k, v in (detrend or {}).items()}
    z_names = list(z)
    priors = priors or {}
    lo = {"tc": x.min() - 1, "k": 1e-3, "a_rs": 1.01, "b": 0.0, "u1": -1.0, "u2": -1.0, "baseline": -np.inf}
    hi = {"tc": x.max() + 1, "k": 0.5, "a_rs": 200.0, "b": 1.5, "u1": 2.0, "u2": 2.0, "baseline": np.inf}

    def model(p):
        v = vals | dict(zip(names, p[: len(names)], strict=True))
        trend = np.exp(sum(c * z[k] for c, k in zip(p[len(names) :], z_names, strict=True))) if z_names else 1.0
        shape = transit(x, period, v["tc"], v["k"], v["a_rs"], _inc(v["a_rs"], v["b"]), "quadratic",
                        (v["u1"], v["u2"]), exposure=exposure)  # fmt: skip
        return v["baseline"] * shape * trend, v

    def resid(p):
        m, v = model(p)
        r = [(f - m) / e]
        r += [np.array([(v[k] - c) / w]) for k, (c, w) in priors.items() if k in v]
        return np.concatenate(r)

    p0 = np.array([vals[n] for n in names] + [0.0] * len(z_names))
    bounds = ([lo[n] for n in names] + [-np.inf] * len(z_names), [hi[n] for n in names] + [np.inf] * len(z_names))
    sol = least_squares(resid, np.clip(p0, *(np.array(b) for b in bounds)), bounds=bounds)
    n, k = len(f), len(sol.x)
    m, v = model(sol.x)
    chi2 = float(np.sum(((f - m) / e) ** 2))
    chi2r = chi2 / max(n - k, 1)
    cov = np.linalg.pinv(sol.jac.T @ sol.jac) * max(chi2r, 1.0)
    errs = dict(zip(names + z_names, np.sqrt(np.clip(np.diag(cov), 0, None)), strict=True))
    v["tc"] += t0
    resid_rel = (f - m) / m
    inc = _inc(v["a_rs"], v["b"])
    out = {"values": {k2: float(v[k2]) for k2 in NAMES} | dict(zip(z_names, map(float, sol.x[len(names) :]),
                                                                      strict=True)), "errors": errs,
           "chi2": chi2, "chi2r": chi2r, "bic": chi2 + k * np.log(n), "dof": n - k,
           "rms_ppt": float(np.std(resid_rel) * 1000), "beta": beta_factor(resid_rel, [5, 10, 20]),
           "model": m, "residuals": f - m}  # fmt: skip
    p_t = sol.x[len(names) :]
    out["trend"] = v["baseline"] * (np.exp(sum(c * z[k2] for c, k2 in zip(p_t, z_names, strict=True))) if z_names
                                    else np.ones(n))  # fmt: skip
    out["derived"] = {"depth_ppt": float(v["k"] ** 2 * 1000), "inc": inc, "t14_h": float(t14(period, v["a_rs"],
                      inc, v["k"]) * 24), "t23_h": float(t23(period, v["a_rs"], inc, v["k"]) * 24),
                      "rho_star": float(density_from_a(v["a_rs"], period))}  # fmt: skip
    out["derived"]["depth_mmag"] = float(-2.5 * np.log10(1 - v["k"] ** 2) * 1000)
    if mcmc_steps:
        out["mcmc"] = _posterior(resid, sol.x, cov, names + z_names, bounds, mcmc_steps, t0, ctx)
    return out


def _posterior(resid, x0, cov, names, bounds, steps, t0, ctx):
    from ..core.inference import mcmc as engine

    scale = np.maximum(np.sqrt(np.clip(np.diag(cov), 0, None)), 1e-8)
    post = engine.around(lambda p: -0.5 * float(np.sum(resid(p) ** 2)), x0, scale, names, *bounds, steps, 1, ctx,
                         (0.3, 1.0))  # fmt: skip
    out = {}
    for i, name in enumerate(names):
        p16, p50, p84 = np.percentile(post.samples[:, i], [16, 50, 84])
        shift = t0 if name == "tc" else 0.0
        out[name] = (float(p50 + shift), float(p50 - p16), float(p84 - p50))
    return {"params": out, "acceptance": post.acceptance, "converged": post.converged}


def planet_radius(k, r_star_sun):
    """(R_Jup, R_Earth) of the planet."""
    r = k * r_star_sun * R_SUN
    return r / R_JUP, r / R_EARTH


def compare_detrending(t, flux, err, period, start, sets, **kw):
    """BIC of each detrending set {label: {name: series}}: the lowest is the one to keep."""
    return {label: fit(t, flux, err, period, start, detrend=d, **kw)["bic"] for label, d in sets.items()}
