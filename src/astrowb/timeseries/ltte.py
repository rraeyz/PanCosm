"""The light-travel-time effect, complete (plans/oc.md OC-6): one or two orbits around the eclipsing pair on a
linear or quadratic ephemeris, found without start values.

Model: T(E) = T0 + P E [+ Q E²] + Σ_orbits A τ(t; P₃, T₃, e, ω), τ = (1 − e²)/(1 + e cos ν) sin(ν + ω) + e sin ω
(Irwin 1952; A = a₁₂ sin i₃ / c in days). For fixed (P₃, T₃, e, ω) of every orbit the model is linear in T0, P,
Q and the A's, so the global search (differential evolution over P₃, the phase of T₃ and √e cos ω, √e sin ω for
each orbit; every population member solved at once) needs no start; least squares then refine all parameters,
and the inference engine samples the posterior on request.
"""

import numpy as np
from scipy.optimize import differential_evolution, least_squares

from ..spectroscopy.orbit import _eccentric_anomaly

AU_PER_LIGHT_DAY = 173.1446326846693
DAYS_PER_YEAR = 365.25


def tau(t, p3, t3, e, omega_deg):
    """The light-time shape (A = 1); arrays broadcast (population members along a leading axis)."""
    m = 2 * np.pi * (t - t3) / p3
    ecc = _eccentric_anomaly(m, e)
    nu = 2 * np.arctan2(np.sqrt(1 + e) * np.sin(ecc / 2), np.sqrt(1 - e) * np.cos(ecc / 2))
    w = np.radians(omega_deg)
    return (1 - e**2) / (1 + e * np.cos(nu)) * np.sin(nu + w) + e * np.sin(w)


def _orbit(x):
    """(P₃, phase of T₃, √e cos ω, √e sin ω) → (P₃, T₃ offset fraction, e, ω in degrees)."""
    p3, phase, c, s = x
    return p3, phase, c * c + s * s, np.degrees(np.arctan2(s, c)) % 360.0


def _solve(times, epochs, w, order, shapes):
    """Weighted linear least squares for every member: shapes (S, n_orbits, N) → (coef (S, k), χ² (S,))."""
    e = epochs[None, :]
    cols = [np.ones_like(shapes[:, 0])] + [np.broadcast_to(e**k, shapes[:, 0].shape) for k in range(1, order + 1)]
    a = np.stack(cols + [shapes[:, j] for j in range(shapes.shape[1])], axis=-1) * w[None, :, None]
    b = times * w
    ata = np.einsum("snk,snl->skl", a, a)
    atb = np.einsum("snk,n->sk", a, b)
    try:
        coef = np.linalg.solve(ata, atb[..., None])[..., 0]
    except np.linalg.LinAlgError:
        coef = np.stack([np.linalg.lstsq(m, v, rcond=None)[0] for m, v in zip(ata, atb, strict=True)])
    r = b[None, :] - np.einsum("snk,sk->sn", a, coef)
    return coef, np.sum(r * r, axis=1)


def _shapes(x, times, t_mid, n_orbits):
    """x (S, 4 n_orbits) → shapes (S, n_orbits, N); bad members (e ≥ 0.95) get NaN."""
    out = []
    for j in range(n_orbits):
        p3, phase, c, s = (x[:, 4 * j + i, None] for i in range(4))
        e = np.minimum(c * c + s * s, 0.95)
        out.append(tau(times[None, :], p3, t_mid + phase * p3, e, np.degrees(np.arctan2(s, c))))
    return np.stack(out, axis=1)


def _de(t, e, err, order, fixed, p3_range, seed, maxiter, popsize):
    """Differential evolution over one more orbit's (P₃, phase, √e cos ω, √e sin ω), the orbits in fixed held
    (their amplitudes solved again with the rest)."""
    t_mid = float(np.median(t))
    rel_t, rel_e, w = t - t_mid, e - np.round(np.median(e)), 1 / err
    fixed = np.asarray(fixed, float).reshape(-1)
    n_orbits = len(fixed) // 4 + 1

    def cost(xt):  # vectorised: xt (4, S)
        x = np.hstack([np.broadcast_to(fixed, (xt.shape[1], len(fixed))), xt.T])
        _coef, chi2 = _solve(rel_t, rel_e, w, order, _shapes(x, t, t_mid, n_orbits))
        bad = xt[2] ** 2 + xt[3] ** 2 >= 0.95
        return np.where(bad | ~np.isfinite(chi2), 1e30, chi2)

    bounds = [p3_range, (0.0, 1.0), (-0.975, 0.975), (-0.975, 0.975)]
    got = differential_evolution(cost, bounds, seed=seed, maxiter=maxiter, popsize=popsize, tol=1e-10,
                                 vectorized=True, polish=False, init="sobol", updating="deferred")  # fmt: skip
    return np.concatenate([fixed, got.x])


def search(times, epochs, errors, n_orbits=1, order=1, p3_range=None, seed=1, maxiter=300, popsize=30):
    """The global search: returns the dict of fit() at the best point found. p3_range: (lo, hi) in days, default
    from twice the median spacing of the minima (at least span / 50) to three times the span. Orbits are found one
    at a time (each search over 4 parameters with the earlier orbits held, then all refined together; a joint
    search over 8 parameters fell into a valley of two orbits of nearly the same period)."""
    t, e, err = (np.asarray(v, float) for v in (times, epochs, errors))
    span = np.ptp(t)
    rng = p3_range or (max(2 * np.median(np.diff(np.sort(t))), span / 50), 3 * span)
    x = np.zeros(0)
    for k in range(n_orbits):
        x = _de(t, e, err, order, x, rng, seed + k, maxiter, popsize)
        if k:  # the earlier orbits again with the new one held: the first was found with the second unmodelled
            for j in range(k):
                others = np.delete(x.reshape(-1, 4), j, axis=0).ravel()
                x = _de(t, e, err, order, others, rng, seed + 10 * k + j, maxiter, popsize)
    result = fit(times, epochs, errors, x, order)
    result["orbits"].sort(key=lambda o: o["P3"])
    return result


def fit(times, epochs, errors, x0, order=1):
    """Least squares of every parameter from the orbits' x0 (4 per orbit: P₃, phase of T₃, √e cos ω, √e sin ω)
    with the linear ones solved first. Returns a dict with the parameters, errors (covariance scaled by √χ²ᵣ),
    χ², BIC, the residuals and the model's parts."""
    t, e, err = (np.asarray(v, float) for v in (times, epochs, errors))
    t_mid = float(np.median(t))
    mid = float(np.round(np.median(e)))
    rel_t, rel_e, w = t - t_mid, e - mid, 1 / err
    x0 = np.asarray(x0, float)
    n_orbits = len(x0) // 4
    coef, _ = _solve(rel_t, rel_e, w, order, _shapes(x0[None, :], t, t_mid, n_orbits))
    k_lin = order + 1

    def model(p):
        lin, nl = p[: k_lin + n_orbits], p[k_lin + n_orbits :]
        poly = sum(lin[k] * rel_e**k for k in range(k_lin))
        sh = _shapes(nl[None, :], t, t_mid, n_orbits)[0]
        return poly + lin[k_lin:] @ sh, poly, lin[k_lin:, None] * sh

    def resid(p):
        return (model(p)[0] - rel_t) * w

    p0 = np.concatenate([coef[0], x0])
    lo = np.full(len(p0), -np.inf)
    hi = np.full(len(p0), np.inf)
    for j in range(n_orbits):
        i = k_lin + n_orbits + 4 * j
        lo[i] = 1e-6
        lo[i + 2 : i + 4], hi[i + 2 : i + 4] = -0.975, 0.975
    sol = least_squares(resid, np.clip(p0, lo + 1e-12, hi - 1e-12), bounds=(lo, hi), x_scale="jac", xtol=1e-12,
                        ftol=1e-12)  # fmt: skip
    n, k = len(t), len(p0)
    chi2 = float(np.sum(sol.fun**2))
    chi2r = chi2 / max(n - k, 1)
    try:
        cov = np.linalg.inv(sol.jac.T @ sol.jac) * max(chi2r, 1.0)
    except np.linalg.LinAlgError:
        cov = np.full((k, k), np.nan)
    total, poly, parts = model(sol.x)
    return _result(sol.x, cov, order, n_orbits, t_mid, mid, chi2, chi2r, n, rel_t - total, poly, parts)


def _result(p, cov, order, n_orbits, t_mid, mid, chi2, chi2r, n, resid, poly, parts):
    k_lin = order + 1
    err = np.sqrt(np.clip(np.diag(cov), 0, None))
    # the polynomial in the caller's numbering (around E = mid): T0 and P at E = 0
    c = p[:k_lin]
    t0 = t_mid + sum(c[k] * (-mid) ** k for k in range(k_lin))
    period = c[1] + (2 * c[2] * (-mid) if order >= 2 else 0.0)
    orbits = []
    for j in range(n_orbits):
        i = k_lin + n_orbits + 4 * j
        p3, phase, sc, ss = p[i : i + 4]
        ecc, w = sc * sc + ss * ss, np.degrees(np.arctan2(ss, sc)) % 360.0
        amp = p[k_lin + j]
        if amp < 0:  # the same orbit seen from the other side: ω + 180°
            amp, w = -amp, (w + 180.0) % 360.0
        jac = np.array([[2 * sc, 2 * ss], [-ss / max(ecc, 1e-12), sc / max(ecc, 1e-12)]])  # ∂(e, ω rad)/∂(c, s)
        sub = jac @ cov[i + 2 : i + 4, i + 2 : i + 4] @ jac.T
        orbits.append({"P3": float(p3), "P3_err": float(err[i]), "T3": float(t_mid + phase * p3),
                       "T3_err": float(np.hypot(err[i + 1] * p3, phase * err[i])), "e": float(ecc),
                       "e_err": float(np.sqrt(max(sub[0, 0], 0))), "omega": float(w),
                       "omega_err": float(np.degrees(np.sqrt(max(sub[1, 1], 0)))), "A": float(amp),
                       "A_err": float(err[k_lin + j])})  # fmt: skip
    return {"T0": float(t0), "P": float(period), "Q": float(c[2]) if order >= 2 else 0.0,
            "Q_err": float(err[2]) if order >= 2 else 0.0, "orbits": orbits, "chi2": chi2, "chi2r": chi2r,
            "n": n, "k": len(p), "bic": chi2 + len(p) * np.log(n), "residuals": resid, "polynomial": poly,
            "ltte": parts, "cov": cov, "params": p, "order": order}  # fmt: skip


def posterior(times, epochs, errors, result, steps=5000, seed=1, ctx=None):
    """The posterior of every parameter around a fit (the shared inference engine; flat priors, e < 0.95):
    {name: (median, minus, plus)} with the orbits' P3, T3, e, omega, A and the ephemeris' T0, P (and Q)."""
    from ..core.inference import mcmc as engine

    t, e, err = (np.asarray(v, float) for v in (times, epochs, errors))
    order, n_orbits = result["order"], len(result["orbits"])
    t_mid, mid = float(np.median(t)), float(np.round(np.median(e)))
    rel_t, rel_e, w = t - t_mid, e - mid, 1 / err
    k_lin = order + 1
    p0 = result["params"]
    scale = np.sqrt(np.clip(np.diag(result["cov"]), 1e-30, None))
    s = max(result["chi2r"], 1.0)

    def log_prob(p):
        nl = p[k_lin + n_orbits :]
        for j in range(n_orbits):
            if nl[4 * j + 2] ** 2 + nl[4 * j + 3] ** 2 >= 0.95 or nl[4 * j] <= 0:
                return -np.inf
        sh = _shapes(nl[None, :], t, t_mid, n_orbits)[0]
        model = sum(p[k] * rel_e**k for k in range(k_lin)) + p[k_lin : k_lin + n_orbits] @ sh
        r = (model - rel_t) * w
        return -0.5 * float(r @ r) / s

    names = [f"x{i}" for i in range(len(p0))]
    post = engine.around(log_prob, p0, scale, names, steps=steps, seed=seed, ctx=ctx)
    rows = []
    for p in post.samples[:: max(1, len(post.samples) // 4000)]:
        r = _result(p, result["cov"], order, n_orbits, t_mid, mid, 0, 1, len(t), None, None, None)
        row = {"T0": r["T0"], "P": r["P"]} | ({"Q": r["Q"]} if order >= 2 else {})
        for j, o in enumerate(r["orbits"]):
            row |= {f"{k}_{j + 1}": o[k] for k in ("P3", "T3", "e", "omega", "A")}
        rows.append(row)
    out = {}
    for key in rows[0]:
        v = np.array([r[key] for r in rows])
        if key.startswith("omega"):
            v = v[0] + (v - v[0] + 180) % 360 - 180
        q = np.percentile(v, [16, 50, 84])
        out[key] = (float(q[1]), float(q[1] - q[0]), float(q[2] - q[1]))
    return {"params": out, "converged": post.converged, "acceptance": post.acceptance}


def derived(orbit, m12=None, span=None):
    """What follows from one orbit: a₁₂ sin i₃ (AU), the mass function (M☉), the minimum third mass and the
    masses at i₃ = 60° and 30° when M₁ + M₂ is given, the semi-amplitude of the systemic velocity (km/s), and the
    number of cycles covered (a warning below 1.5)."""
    from scipy.optimize import brentq

    a_au = orbit["A"] * AU_PER_LIGHT_DAY
    p_yr = orbit["P3"] / DAYS_PER_YEAR
    f_m = a_au**3 / p_yr**2
    k_kms = 2 * np.pi * a_au * 1.495978707e8 / (orbit["P3"] * 86400 * np.sqrt(1 - orbit["e"] ** 2))
    out = {"a12_sini_au": a_au, "f_m3": f_m, "K_kms": k_kms}
    if m12:
        for label, incl in (("m3_min", 90.0), ("m3_60", 60.0), ("m3_30", 30.0)):
            s3 = np.sin(np.radians(incl)) ** 3
            out[label] = float(brentq(lambda m, s3=s3: (m**3 * s3) / (m12 + m) ** 2 - f_m, 1e-6, 1e4))
    if span:
        out["cycles"] = span / orbit["P3"]
        out["coverage_warning"] = out["cycles"] < 1.5
    return out


def stable(p_in, p_out, e_out, m12, m3, incl_mutual_deg=0.0):
    """Mardling & Aarseth 2001: the hierarchy is stable when a_out / a_in exceeds
    2.8 (1 + q_out)^(2/5) (1 + e_out)^(2/5) (1 − e_out)^(−6/5) (1 − 0.3 i/180°), q_out = m3 / m12.
    Returns (stable, the ratio, the limit)."""
    ratio = ((p_out / p_in) ** 2 * (m12 + m3) / m12) ** (1 / 3)
    q = m3 / m12
    limit = 2.8 * (1 + q) ** 0.4 * (1 + e_out) ** 0.4 * (1 - e_out) ** -1.2 * (1 - 0.3 * incl_mutual_deg / 180)
    return ratio > limit, float(ratio), float(limit)


def residual_periodogram(times, residuals, errors, p_min=None, p_max=None):
    """The GLS periodogram of the O−C residuals after the polynomial, to justify a periodic term before fitting it:
    (periods, power, best period, its false-alarm probability (Baluev) over the searched range)."""
    from .methods import gls
    from .significance import fap_baluev

    t = np.asarray(times, float)
    span = np.ptp(t)
    p_min = p_min or max(2 * np.median(np.diff(np.sort(t))), span / 50)
    p_max = p_max or 3 * span
    periods, power, best = gls(t, residuals, errors, p_min, p_max)
    peak = float(np.max(power))
    return periods, power, best, fap_baluev(t - t.min(), residuals, errors, peak, 1 / p_max, 1 / p_min)
