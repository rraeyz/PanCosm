"""Apsidal motion, complete (plans/oc.md OC-7): the exact times of minima (Lacy 1992: the instant of least
projected separation, Kepler's equation solved, any e and inclination), the fit of T0, Pₛ, e, ω₀ and ω̇ from a
grid, and what follows: Pₐ, U, ω̇ per year, the relativistic share and the observed k₂.

Convention as models.eb: ω of star 1's orbit, the primary minimum near ν = 90° − ω, the secondary near 270° − ω;
ω(E) = ω₀ + ω̇ E (degrees, E the cycle). Periastron passes every anomalistic period Pₐ = Pₛ / (1 − ω̇ / 360°);
each minimum falls at T_peri(E) + Pₐ M(E) / 2π with M its mean anomaly, the branch followed continuously.
"""

import numpy as np
from scipy.optimize import least_squares

SECONDS_PER_YEAR = 365.25 * 86400


def _separation2(nu, w, e, s2):
    r = (1 - e * e) / (1 + e * np.cos(nu))
    return r * r * (1 - s2 * np.sin(nu + w) ** 2)


def conjunction_anomaly(w, e, incl_deg, secondary, iterations=12):
    """The true anomaly of least projected separation (radians, continuous in ω: no wrapping)."""
    nu = (1.5 if secondary else 0.5) * np.pi - w
    s2 = np.sin(np.radians(incl_deg)) ** 2
    if s2 >= 1 - 1e-15 or e == 0:
        return nu
    h = 1e-4
    for _ in range(iterations):  # Newton on the derivative, by central differences
        f0, fp, fm = _separation2(nu, w, e, s2), _separation2(nu + h, w, e, s2), _separation2(nu - h, w, e, s2)
        d1, d2 = (fp - fm) / (2 * h), (fp - 2 * f0 + fm) / (h * h)
        step = np.where(d2 > 0, d1 / np.where(d2 > 0, d2, 1.0), 0.0)
        nu = nu - np.clip(step, -0.1, 0.1)
    return nu


def _mean_anomaly(nu, e):
    """Continuous: the 2π turns of ν carried over."""
    turns = np.floor((nu + np.pi) / (2 * np.pi))
    v = nu - 2 * np.pi * turns
    ecc = 2 * np.arctan2(np.sqrt(1 - e) * np.sin(v / 2), np.sqrt(1 + e) * np.cos(v / 2))
    return ecc - e * np.sin(ecc) + 2 * np.pi * turns


def times(epochs, t0, ps, e, omega0, d_omega, incl=90.0):
    """Exact times of minima; epochs: integers for primaries, half-integers for secondaries. T0 is the primary at
    E = 0, Pₛ the sidereal period (days), ω̇ in degrees per cycle."""
    ep = np.asarray(epochs, float)
    secondary = np.abs(ep % 1 - 0.5) < 1e-6
    cycle = np.where(secondary, ep - 0.5, ep)
    pa = ps / (1 - d_omega / 360.0)
    w = np.radians(omega0 + d_omega * cycle)
    m = np.where(secondary, _mean_anomaly(conjunction_anomaly(w, e, incl, True), e),
                 _mean_anomaly(conjunction_anomaly(w, e, incl, False), e))  # fmt: skip
    w0 = np.radians(omega0)
    m0 = _mean_anomaly(conjunction_anomaly(w0, e, incl, False), e)
    return t0 + pa * cycle + pa * (m - m0) / (2 * np.pi)


def fit(epochs, observed, errors, incl=90.0, e_grid=None, rate_grid=None, start=None):
    """T0, Pₛ, e, ω₀, ω̇ by least squares from the best point of a grid over e and ω̇ (with ω₀ on a grid too and
    T0, Pₛ solved linearly there). Returns the parameters, their errors, χ² and the grid's χ² map (e × ω̇) that
    shows the e–ω̇ valley. start: (T0, Pₛ, e, ω₀, ω̇) to refine without the grid (no map then)."""
    ep, t, err = (np.asarray(v, float) for v in (epochs, observed, errors))
    sec = np.abs(ep % 1 - 0.5) < 1e-6
    if sec.sum() < 3 or (~sec).sum() < 3:
        raise ValueError("apsidal motion needs at least 3 primary and 3 secondary minima")
    cycle = np.where(sec, ep - 0.5, ep)
    span = np.ptp(cycle)
    e_grid = np.linspace(0.02, 0.6, 30) if e_grid is None else e_grid
    rate_grid = np.geomspace(360 / (30 * span), 360 / (span / 4), 60) if rate_grid is None else rate_grid
    w = 1 / err
    best, chi_map = None, np.full((len(e_grid), len(rate_grid)), np.inf)
    if start is not None:
        best = (0.0, *start)
        e_grid = rate_grid = []
    ps0 = np.polyfit(cycle[~sec], t[~sec], 1)[0]
    omegas = np.arange(0, 360, 30.0)[:, None] if start is None else np.zeros((1, 1))  # every ω₀ at once (rows)
    a = np.column_stack([np.ones_like(t), cycle]) * w[:, None]
    proj = a @ np.linalg.pinv(a)  # the fitted T0 + Pₛ E of any data vector
    for i, ecc in enumerate(e_grid):
        for j, rate in enumerate(rate_grid):
            shape = times(ep[None, :], 0.0, ps0, ecc, omegas, rate, incl) - ps0 / (1 - rate / 360) * cycle
            y = (t[None, :] - shape) * w
            r = y - y @ proj.T
            chi2 = np.sum(r * r, axis=1)
            k = int(np.argmin(chi2))
            chi_map[i, j] = chi2[k]
            if best is None or chi2[k] < best[0]:
                coef = np.linalg.lstsq(a, y[k], rcond=None)[0]
                best = (float(chi2[k]), coef[0], ps0, ecc, float(omegas[k, 0]), rate)
    t_ref = float(np.round(np.median(t)))

    rel = t - t_ref  # relative times: at 2.45e6 the finite differences of the Jacobian drown in rounding

    def resid(p):
        return (times(ep, p[0], p[1], p[2], p[3], p[4], incl) - rel) * w

    p0 = np.array([best[1] - t_ref, best[2], best[3], best[4], best[5]])
    sol = least_squares(resid, p0, bounds=([-np.inf, 0, 0, -np.inf, -np.inf], [np.inf, np.inf, 0.95, np.inf, np.inf]),
                        x_scale="jac", xtol=1e-14, ftol=1e-14)  # fmt: skip
    chi2 = float(np.sum(sol.fun**2))
    chi2r = chi2 / max(len(t) - 5, 1)
    cov = np.linalg.inv(sol.jac.T @ sol.jac) * max(chi2r, 1.0)
    err_p = np.sqrt(np.diag(cov))
    names = ("T0", "Ps", "e", "omega0", "d_omega")
    out = {n: float(v) for n, v in zip(names, sol.x, strict=True)}
    out["T0"] += t_ref
    out["omega0"] %= 360.0
    out |= {n + "_err": float(v) for n, v in zip(names, err_p, strict=True)}
    out |= {"chi2": chi2, "chi2r": chi2r, "cov": cov, "map": chi_map, "e_grid": e_grid, "rate_grid": rate_grid,
            "residuals": sol.fun / w, "incl": incl}  # fmt: skip
    return out


def derived(f):
    """Pₐ, U (years) and ω̇ (degrees per year), with errors."""
    ps, rate = f["Ps"], f["d_omega"]
    pa = ps / (1 - rate / 360.0)
    u_yr = 360.0 / rate * ps / 365.25
    return {
        "Pa": pa,
        "U_years": u_yr,
        "U_years_err": u_yr * f["d_omega_err"] / rate,
        "omega_dot_per_year": rate / ps * 365.25,
        "omega_dot_per_year_err": f["d_omega_err"] / ps * 365.25,
    }


def relativistic(m1, m2, period_days, e):
    """The general-relativistic apsidal rate (Giménez 1985): 5.45 × 10⁻⁴ (M₁ + M₂)^(2/3) / ((1 − e²) P^(2/3))
    degrees per cycle (masses in M☉, P in days)."""
    return 5.45e-4 * ((m1 + m2) / period_days) ** (2 / 3) / (1 - e * e)


def k2_observed(classical_deg_per_cycle, e, m1, m2, r1, r2, spin1=None, spin2=None):
    """The observed mean internal-structure constant k̄₂ = (ω̇_cl / 360°) / (c₂₁ + c₂₂), the c₂ᵢ of the tidal and
    rotational distortion (Kopal 1978; fractional radii r, rotation F as a share of the orbital rate, default the
    pseudo-synchronous value of models.orbit_terms)."""
    from ..models.orbit_terms import pseudo_synchronous

    f = (1 - e * e) ** -2
    g = (8 + 12 * e * e + e**4) / (8 * (1 - e * e) ** 5)
    ps = pseudo_synchronous(e)
    s1, s2 = ps if spin1 is None else spin1, ps if spin2 is None else spin2
    c1 = r1**5 * (s1 * s1 * (1 + m2 / m1) * f + 15 * m2 / m1 * g)
    c2 = r2**5 * (s2 * s2 * (1 + m1 / m2) * f + 15 * m1 / m2 * g)
    return classical_deg_per_cycle / 360.0 / (c1 + c2)
