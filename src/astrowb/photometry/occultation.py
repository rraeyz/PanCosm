"""Occultation timing (PHO-38): a square-well fit of a light curve.

Model: flux = base outside [D, R], bottom inside; frame i integrates over [t_i - dt/2, t_i + dt/2], so an edge
inside a frame gives the time-weighted mix of the two levels. D and R are found by least squares (a grid over the
edge positions, refined once; the two levels are linear for given edges). Their errors: bootstrap of residuals.
"""

import numpy as np


def _fit(t, y, w, dt, d_grid, r_grid):
    """(chi2, D, R, base, bottom) of the best edge pair on the grids."""
    lo, hi = t - dt / 2, t + dt / 2
    best = (np.inf, 0.0, 0.0, 0.0, 0.0)
    for d in d_grid:
        r = r_grid[r_grid > d]
        if not len(r):
            continue
        f = np.clip(np.minimum(r[:, None], hi) - np.maximum(d, lo), 0, None) / dt  # (nR, n) share inside
        a, b = 1 - f, f
        saa, sab, sbb = (w * a * a).sum(1), (w * a * b).sum(1), (w * b * b).sum(1)
        say, sby = (w * a * y).sum(1), (w * b * y).sum(1)
        det = saa * sbb - sab**2
        det = np.where(det > 1e-12 * np.maximum(saa * sbb, 1e-300), det, np.nan)
        base, bottom = (sbb * say - sab * sby) / det, (saa * sby - sab * say) / det
        chi = (w * (y - a * base[:, None] - b * bottom[:, None]) ** 2).sum(1)
        chi = np.where(np.isnan(chi), np.inf, chi)
        k = int(np.argmin(chi))
        if chi[k] < best[0]:
            best = (float(chi[k]), float(d), float(r[k]), float(base[k]), float(bottom[k]))
    return best


def _search(t, y, w, dt):
    grid = np.arange(t[0] - dt / 2, t[-1] + dt, dt)
    _, d, r, _, _ = _fit(t, y, w, dt, grid, grid)
    fine = np.linspace(-dt, dt, 41)
    return _fit(t, y, w, dt, d + fine, r + fine)


def _model(t, dt, d, r, base, bottom):
    f = np.clip(np.minimum(r, t + dt / 2) - np.maximum(d, t - dt / 2), 0, None) / dt
    return base * (1 - f) + bottom * f


def fit_occultation(times, flux, errors=None, nboot=100, rng=None):
    """Square-well fit of an evenly sampled light curve (times of frame centres, seconds). Returns a dict of
    floats: base, bottom, D, R, duration, mag_drop (None if the bottom is not positive), D_err, R_err,
    duration_err (bootstrap standard deviations; rng: a seed or numpy Generator)."""
    t, y = np.asarray(times, float), np.asarray(flux, float)
    if t.ndim != 1 or t.shape != y.shape or len(t) < 6:
        raise ValueError("an occultation fit needs matching times and flux, at least 6 points")
    dt = float(np.median(np.diff(t)))
    if not dt > 0:
        raise ValueError("times must increase")
    w = np.ones_like(y) if errors is None else 1 / np.asarray(errors, float) ** 2
    chi, d, r, base, bottom = _search(t, y, w, dt)
    if not np.isfinite(chi):
        raise ValueError("no square-well fit found in this light curve")
    model = _model(t, dt, d, r, base, bottom)
    resid = y - model
    gen = np.random.default_rng(rng)
    boot = [_search(t, model + gen.choice(resid, len(resid)), w, dt)[1:3] for _ in range(nboot)]
    sd = np.std(boot, axis=0) if boot else (np.nan, np.nan)
    dur_err = float(np.std([b[1] - b[0] for b in boot])) if boot else float("nan")
    return {
        "base": base,
        "bottom": bottom,
        "D": d,
        "R": r,
        "duration": r - d,
        "mag_drop": float(-2.5 * np.log10(bottom / base)) if bottom > 0 and base > 0 else None,
        "D_err": float(sd[0]),
        "R_err": float(sd[1]),
        "duration_err": dur_err,
    }
