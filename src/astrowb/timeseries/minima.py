"""Times of minimum (eclipses, transits) and O-C.

Kwee & van Woerden (1956, BAN 12, 327): the light curve is interpolated on an even grid,
folded about trial times T, and S(T) = sum of squared differences between the two branches
is fitted by a parabola; its minimum is the time of minimum with
    sigma^2 = (4ac - b^2) / (4a^2 (Z - 1)),   Z = number of independent point pairs.
Classic KvW uses Z = N/4 and is known to underestimate the error for noisy data
(Deeg 2020, Galaxies 9, 1). We therefore also give a bootstrap error (resampling residuals
of a symmetric fit) and report the larger of the two by default.

Polynomial method: least-squares parabola around the minimum.

Trapezoid fit: symmetric trapezoid (mid-time, depth, total duration, ingress duration) times a
linear baseline, least squares; errors from the covariance scaled by the reduced chi^2 when it
is above 1. Best for flat-bottomed transits, where KvW's S(T) is shallow and noisy.
"""

import numpy as np


def _s_curve(t, y, trial, half_width, n_grid):
    dt = np.linspace(0, half_width, n_grid)
    left = np.interp(trial - dt, t, y)
    right = np.interp(trial + dt, t, y)
    return np.mean((left - right) ** 2)


def kwee_van_woerden(t, y, n_trials=61, bootstrap=200, seed=0):
    """Return (t_min, sigma_kvw, sigma_bootstrap). t must cover both branches of the minimum.

    S(T) is computed on a grid of trial times spanning a third of the usable half-width; the
    parabola is fitted to the 9 grid points around the smallest S, where S is parabolic."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    order = np.argsort(t)
    t, y = t[order], y[order]
    ys = _smooth(y)
    depth = np.clip(np.median(ys) - ys, 0, None)  # centroid of the dip: robust for flat-bottomed transits
    t0 = float(np.sum(depth * t) / np.sum(depth)) if depth.sum() > 0 else t[np.argmin(ys)]
    if min(t0 - t[0], t[-1] - t0) <= 0 or np.argmin(ys) in (0, len(y) - 1):
        raise ValueError("the minimum must have data on both sides")

    def solve(yy, centre, tries=3):
        half = min(centre - t[0], t[-1] - centre)
        span = half / 3
        hw = half - span  # same half-width for every trial, so the S values are comparable
        n_grid = max(8, int(np.sum(np.abs(t - centre) <= hw)))
        trials = centre + np.linspace(-span, span, n_trials)
        s = np.array([_s_curve(t, yy, tr, hw, n_grid) for tr in trials])
        j = int(np.argmin(s))
        if not 4 <= j <= n_trials - 5:  # minimum at the grid edge: move the grid there and retry
            if tries == 0:
                raise ValueError("no minimum found")
            return solve(yy, trials[j], tries - 1)
        a, b, c = np.polyfit(trials[j - 4 : j + 5] - centre, s[j - 4 : j + 5], 2)
        if a <= 0:
            raise ValueError("no minimum found")
        z = np.sum(np.abs(t - centre) <= hw) / 4  # independent pairs (KvW: N/4)
        var = (4 * a * c - b * b) / (4 * a * a * (z - 1))
        return centre - b / (2 * a), np.sqrt(max(var, 0.0))

    tmin, sig = solve(y, t0)
    tmin, sig = solve(y, tmin)  # second pass centred on the first estimate
    boot = np.nan
    if bootstrap:
        rng = np.random.default_rng(seed)
        model = 0.5 * (y + np.interp(2 * tmin - t, t, y))  # symmetric about tmin
        resid = y - model
        samples = []
        for _ in range(bootstrap):
            try:
                samples.append(solve(model + rng.choice(resid, len(resid)), tmin)[0])
            except ValueError:
                pass
        boot = float(np.std(samples)) if len(samples) > 10 else np.nan
    return float(tmin), float(sig), float(boot)


def polynomial_minimum(t, y):
    """Minimum of a least-squares parabola fitted to the points given (select them around the
    minimum first); returns (t_min, sigma) with sigma from the fit covariance."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    t0 = t[np.argmin(_smooth(y))]
    (a, b, _), cov = np.polyfit(t - t0, y, 2, cov=True)
    tm = -b / (2 * a)
    grad = np.array([b / (2 * a * a), -1 / (2 * a)])  # d tm / d(a, b)
    return float(t0 + tm), float(np.sqrt(grad @ cov[:2, :2] @ grad))


def _trapezoid(t, t0, depth, t14, tin, base, slope):
    x = np.abs(t - t0)
    shape = np.clip((t14 / 2 - x) / max(tin, 1e-9), 0, 1)
    return base * (1 + slope * (t - t0)) * (1 - depth * shape)


def trapezoid_fit(t, y, err=None):
    """Return dict: t0, t0_err, depth, depth_err, t14, t14_err, tin, chi2r (meaningful only with err)."""
    from scipy.optimize import least_squares

    t_abs, y = np.asarray(t, float), np.asarray(y, float)
    tref = float(np.round(t_abs.mean(), 1))
    t = t_abs - tref  # a JD of 2.4e6 would make the numerical derivative step ~1 hour
    w = np.ones_like(y) if err is None else 1 / np.asarray(err, float)
    ys = _smooth(y)
    base = np.median(y)
    depth = np.clip(base - ys, 0, None)
    t0 = float(np.sum(depth * t) / np.sum(depth)) if depth.sum() > 0 else t[np.argmin(ys)]
    span = t[-1] - t[0]
    p0 = [t0, max(1 - ys.min() / base, 1e-3), span / 2, span / 12, base, 0.0]
    lo = [t[0], 0, span / 50, span / 500, 0, -np.inf]
    hi = [t[-1], 1, 2 * span, span, np.inf, np.inf]
    res = least_squares(lambda p: (_trapezoid(t, *p) - y) * w, p0, bounds=(lo, hi), x_scale="jac")
    dof = max(1, len(y) - len(p0))
    chi2r = float(np.sum(res.fun**2) / dof)
    # without given errors the residual variance is the noise estimate; with errors, only inflate
    cov = np.linalg.pinv(res.jac.T @ res.jac) * (chi2r if err is None else max(chi2r, 1.0))
    e = np.sqrt(np.diag(cov))
    p = res.x
    p[0] += tref
    return {
        "t0": float(p[0]),
        "t0_err": float(e[0]),
        "depth": float(p[1]),
        "depth_err": float(e[1]),
        "t14": float(p[2]),
        "t14_err": float(e[2]),
        "tin": float(p[3]),
        "chi2r": chi2r,
    }


def _smooth(y, k=5):
    """Running mean (odd width, edges padded with edge values) to locate the minimum robustly."""
    k = max(1, min(k, len(y) // 5))
    k -= 1 - k % 2  # odd width keeps the length
    return np.convolve(np.pad(y, k // 2, mode="edge"), np.ones(k) / k, mode="valid")


def o_minus_c(times, t0, period):
    """Epoch (nearest integer) and O-C in the units of the inputs (days)."""
    times = np.asarray(times, float)
    epoch = np.round((times - t0) / period)
    return epoch.astype(int), times - (t0 + epoch * period)
