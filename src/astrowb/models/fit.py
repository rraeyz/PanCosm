"""Fitting the eclipsing-binary / transit model, and absolute dimensions from light + RV solutions.

Fitted parameters (JKTEBOP-style, well-conditioned): r_sum = r1 + r2, k = r2 / r1, incl, j, e cos w,
e sin w, l3, t0, period, and a flux scale (always free). Any subset can be fixed. Errors come
from the covariance matrix, scaled by sqrt(chi2_r) when the data have no errors or chi2_r > 1.

Absolute dimensions (e.g. Southworth 2015): from the light curve sin i, r1, r2 and from the SB2
orbit M sin^3 i and a sin i:  M = M sin^3 i / sin^3 i, a = a sin i / sin i, R = r a,
log g = log10(G M / R^2) (cgs). Errors by Monte Carlo from both solutions' errors.
"""

import numpy as np

from .. import sampling
from . import eb

G_CGS = 6.67430e-8
M_SUN_G = 1.98847e33
R_SUN_CM = 6.957e10

NAMES = ("period", "t0", "r_sum", "k", "incl", "j", "ecosw", "esinw", "l3")
BOUNDS = {
    "period": (0, np.inf),
    "t0": (-np.inf, np.inf),
    "r_sum": (1e-4, 0.8),
    "k": (1e-3, 20.0),
    "incl": (30.0, 90.0),
    "j": (0.0, 50.0),
    "ecosw": (-0.95, 0.95),
    "esinw": (-0.95, 0.95),
    "l3": (-0.5, 0.95),
}
DEFAULT_FREE = {"t0", "r_sum", "k", "incl", "j"}


def _orbit(ecosw, esinw):
    e = float(np.hypot(ecosw, esinw))
    return e, float(np.degrees(np.arctan2(esinw, ecosw))) if e > 0 else 90.0


def model(t, p, ld1=(0.0, 0.0), ld2=(0.0, 0.0)):
    """Normalised model flux for a parameter dict with the NAMES keys; p["exposure"] (seconds, optional): the flux
    averaged over each exposure, as a long cadence records it (TESS 30 min, Kepler 29.4 min; Kipping 2010)."""
    r1 = p["r_sum"] / (1 + p["k"])
    e, w = _orbit(p["ecosw"], p["esinw"])

    def flux(tt):
        return eb.light_curve(
            tt, p["period"], p["t0"], r1, p["k"] * r1, p["incl"], p["j"], e, w, tuple(ld1), tuple(ld2), p["l3"]
        )

    exposure = float(p.get("exposure") or 0.0)
    if exposure <= 0:
        return flux(t)
    from .orbit_terms import integrate_exposure

    # one sub-sample per 2 min, odd, 3 to 15: Kipping's rule of thumb keeps the smearing error far below TESS noise
    n = min(15, max(3, int(np.ceil(exposure / 120)) | 1))
    return integrate_exposure(flux, t, exposure / 86400.0, n=n)


def fit_light_curve(t, flux, err=None, start=None, free=None, ld1=(0.0, 0.0), ld2=(0.0, 0.0)):
    """Least-squares fit. start: dict of initial values (period and t0 required); free: names to fit.
    Returns dict(params, errors, derived, chi2r, rms, scale, n)."""
    t, flux = np.asarray(t, float), np.asarray(flux, float)
    ok = np.isfinite(t) & np.isfinite(flux)
    w = np.ones_like(flux) if err is None else 1 / np.asarray(err, float)
    ok &= np.isfinite(w)
    t, flux, w = t[ok], flux[ok], w[ok]
    p = {"r_sum": 0.2, "k": 0.8, "incl": 88.0, "j": 0.8, "ecosw": 0.0, "esinw": 0.0, "l3": 0.0} | dict(start or {})
    if "period" not in p or "t0" not in p:
        raise ValueError("give the period and the time of primary minimum")
    free = [n for n in NAMES if n in (DEFAULT_FREE if free is None else set(free))]
    tref = float(np.round(np.median(t), 1))  # small numbers for the numerical derivatives
    p["t0"] -= tref
    for n in free:
        lo, hi = BOUNDS[n]
        p[n] = float(np.clip(p[n], lo + 1e-9 if np.isfinite(lo) else lo, hi - 1e-9 if np.isfinite(hi) else hi))
    x0 = [p[n] for n in free] + [float(np.median(flux[flux >= np.percentile(flux, 50)]))]
    lo = [BOUNDS[n][0] for n in free] + [0.0]
    hi = [BOUNDS[n][1] for n in free] + [np.inf]

    def unpack(x):
        q = dict(p)
        q.update(zip(free, x[:-1], strict=True))
        return q, x[-1]

    def resid(x):
        q, scale = unpack(x)
        return (scale * model(t - tref, q, ld1, ld2) - flux) * w

    from scipy.optimize import least_squares

    res = least_squares(resid, x0, bounds=(lo, hi), x_scale="jac")
    dof = max(1, len(flux) - len(x0))
    chi2r = float(np.sum(res.fun**2) / dof)
    cov = np.linalg.pinv(res.jac.T @ res.jac) * (chi2r if err is None else max(chi2r, 1.0))
    sd = np.sqrt(np.clip(np.diag(cov), 0, None))
    q, scale = unpack(res.x)
    q["t0"] += tref
    errors = {n: 0.0 for n in NAMES} | dict(zip(free, sd[:-1].tolist(), strict=True))
    # derived quantities and their errors by sampling the covariance
    draws = sampling.draws(res.x, cov, 3000)
    der = []
    for d in draws:
        qq, _ = unpack(d)
        r1 = qq["r_sum"] / (1 + qq["k"])
        e, om = _orbit(qq["ecosw"], qq["esinw"])
        der.append((r1, qq["k"] * r1, e, om, eb.light_ratio(r1, qq["k"] * r1, qq["j"], ld1, ld2)))
    der = np.array(der)
    r1 = q["r_sum"] / (1 + q["k"])
    e, om = _orbit(q["ecosw"], q["esinw"])
    derived = {
        "r1": r1,
        "r2": q["k"] * r1,
        "e": e,
        "omega": om % 360,
        "light_ratio": eb.light_ratio(r1, q["k"] * r1, q["j"], ld1, ld2),
    }
    derived_err = {
        "r1": float(np.std(der[:, 0])),
        "r2": float(np.std(der[:, 1])),
        "e": float(np.std(der[:, 2])),
        "omega": float(np.std(np.degrees(np.unwrap(np.radians(der[:, 3]))))),
        "light_ratio": float(np.std(der[:, 4])),
    }
    resid_flux = res.fun / w
    return {
        "params": q,
        "errors": errors,
        "free": free,
        "derived": derived,
        "derived_err": derived_err,
        "scale": float(scale),
        "chi2r": chi2r,
        "rms": float(np.std(resid_flux)),
        "n": int(len(flux)),
        "ld1": list(ld1),
        "ld2": list(ld2),
    }


def absolute_dimensions(lc, orbit, n=5000, seed=1):
    """Masses, radii, separation and surface gravities from a light-curve fit (fit_light_curve) and a
    double-lined orbit (spectroscopy.orbit.fit_sb2). Values and Monte-Carlo errors.
    The masses and the separation are computed from the same draws of K1, K2, e and P (as JKTABSDIM does), not
    drawn on their own: they are strongly correlated, and log g then depends on K2, P, r and i only (Southworth
    2015); independent draws inflated the log g errors several times."""
    from ..spectroscopy.orbit import sb2_dimensions

    rng = np.random.default_rng(seed)

    def draw(value, error):
        return value + (error or 0.0) * rng.standard_normal(n)

    incl = np.radians(np.clip(draw(lc["params"]["incl"], lc["errors"]["incl"]), 1, 90))
    s = np.sin(incl)
    r1 = draw(lc["derived"]["r1"], lc["derived_err"]["r1"])
    r2 = draw(lc["derived"]["r2"], lc["derived_err"]["r2"])
    m1, m2, asini = sb2_dimensions(
        draw(orbit["period"], orbit.get("period_err")),
        np.clip(draw(orbit["e"], orbit.get("e_err")), 0, 0.99),
        draw(orbit["k"], orbit.get("k_err")),
        draw(orbit["k2"], orbit.get("k2_err")),
    )
    m1, m2, a = m1 / s**3, m2 / s**3, asini / s
    rad1, rad2 = r1 * a, r2 * a
    logg1 = np.log10(G_CGS * m1 * M_SUN_G / (rad1 * R_SUN_CM) ** 2)
    logg2 = np.log10(G_CGS * m2 * M_SUN_G / (rad2 * R_SUN_CM) ** 2)
    out = {}
    for name, v in (("m1", m1), ("m2", m2), ("a", a), ("r1", rad1), ("r2", rad2), ("logg1", logg1), ("logg2", logg2)):
        out[name] = float(np.median(v))
        out[name + "_err"] = float(np.std(v))
    return out


def roche_check(r1, r2, q=None):
    """How far the spheres model holds for fractional radii r1, r2 (q = M2/M1; 1 when unknown).
    "contact": a star fills at least 90 % of its Roche lobe (Eggleton 1983, volume-equivalent radius) - a
    semi-detached or contact (W UMa) binary, which needs a Roche model (PHOEBE, Wilson-Devinney);
    "distorted": a radius above 0.25 a, where tidal flattening of a few per cent makes EBOP-type sphere models
    approximate (Popper & Etzel 1981; Southworth 2008); otherwise None."""

    def lobe(x):  # lobe radius / a of a star with mass ratio x = M_this / M_other
        c = x ** (2 / 3)
        return 0.49 * c / (0.6 * c + np.log1p(x ** (1 / 3)))

    q = q or 1.0
    lobe1, lobe2 = lobe(1 / q), lobe(q)
    fill = max(r1 / lobe1, r2 / lobe2)
    level = "contact" if fill >= 0.9 else "distorted" if max(r1, r2) > 0.25 else None
    return {"level": level, "fill": float(fill), "lobe1": float(lobe1), "lobe2": float(lobe2), "q": float(q)}


def mcmc(t, flux, err, result, free=None, ld1=(0.0, 0.0), ld2=(0.0, 0.0), steps=2000, ctx=None, seed=1):
    """Posterior of the free parameters around a least-squares result (the shared inference engine:
    differential-evolution chains that stop when converged, at most `steps` generations). Flat priors inside
    BOUNDS. Without errors the noise is taken from the fit's rms. Returns {name: (median, minus, plus)} (16th /
    84th percentiles), the samples (thinned), the acceptance fraction and whether the chains converged."""
    from ..core.inference import mcmc as engine

    t, flux = np.asarray(t, float), np.asarray(flux, float)
    sigma = np.full(len(t), result["rms"]) if err is None else np.asarray(err, float)
    ok = np.isfinite(t) & np.isfinite(flux) & np.isfinite(sigma)
    t, flux, sigma = t[ok], flux[ok], sigma[ok]
    free = [n for n in NAMES if n in (DEFAULT_FREE if free is None else set(free))]
    base = dict(result["params"])
    tref = float(np.round(np.median(t), 1))
    x0 = np.array([base[n] - (tref if n == "t0" else 0.0) for n in free] + [result["scale"]])
    scale0 = np.array([max(result["errors"].get(n, 0.0), 1e-6) for n in free] + [1e-4 * result["scale"]])
    lo = np.array([BOUNDS[n][0] for n in free] + [0.0])
    hi = np.array([BOUNDS[n][1] for n in free] + [np.inf])

    def log_prob(x):
        q = base | dict(zip(free, x[:-1], strict=True))
        r = (x[-1] * model(t - tref, q, ld1, ld2) - flux) / sigma
        return -0.5 * float(r @ r)

    post = engine.around(log_prob, x0, scale0, [*free, "scale"], lo, hi, steps, seed, ctx, (0.2, 1.0))
    chain = post.samples.copy()
    chain[:, [i for i, n in enumerate(free) if n == "t0"]] += tref
    rng = np.random.default_rng(seed)
    out = {}
    for i, n in enumerate(free):
        p16, p50, p84 = np.percentile(chain[:, i], [16, 50, 84])
        out[n] = (float(p50), float(p50 - p16), float(p84 - p50))
    keep = chain[rng.choice(len(chain), min(len(chain), 3000), replace=False)]
    return {
        "params": out,
        "names": free,
        "samples": keep[:, :-1].tolist(),
        "acceptance": post.acceptance,
        "converged": post.converged,
    }
