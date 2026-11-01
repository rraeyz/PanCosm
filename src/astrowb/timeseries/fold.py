"""Folding and refining a period (plans/period.md PER-5): the binned folded curve, the period refined by a harmonic
fit with its error, an eclipsing binary's two minima, and the test "P or 2P?".

    phase, flux, err = binned(t, y, period, t0)
    period, error = refine(t, y, period)                  # a Fourier series of n harmonics with the frequency free
    ecl = eclipses(t, y, period, t0)                      # depths, widths, phase of the secondary, e cos ω
    which = p_or_2p(t, y, period, t0)                     # {"period": the orbital one, "z": significance}
"""

import numpy as np

from .period import fold


def binned(t, y, period, t0=0.0, bins=50):
    """(phase centres in 0 … 1, median per bin, its error 1.2533 σ / √n); empty bins left out."""
    phase = fold(t, period, t0) % 1.0
    y = np.asarray(y, float)
    which = np.minimum((phase * bins).astype(int), bins - 1)
    centres, med, err = [], [], []
    for b in range(bins):
        inside = y[which == b]
        if inside.size:
            centres.append((b + 0.5) / bins)
            med.append(np.median(inside))
            err.append(1.2533 * np.std(inside) / np.sqrt(inside.size) if inside.size > 1 else np.nan)
    return np.array(centres), np.array(med), np.array(err)


def refine(t, y, period, n_harmonics=4, err=None):
    """(period, its 1σ error): least squares of a mean and n harmonics with the frequency free, started at 1/period;
    the error from the covariance scaled by χ²ᵣ."""
    from scipy.optimize import least_squares

    t = np.asarray(t, float)
    t = t - t.mean()  # the frequency and the phases decouple about the middle of the data
    y = np.asarray(y, float)
    w = np.ones_like(y) if err is None else 1 / np.asarray(err, float)
    k = np.arange(1, n_harmonics + 1)

    def design(f):
        arg = 2 * np.pi * f * t[:, None] * k
        return np.column_stack([np.ones_like(t), np.cos(arg), np.sin(arg)])

    f0 = 1 / period
    coef0 = np.linalg.lstsq(design(f0) * w[:, None], y * w, rcond=None)[0]

    def resid(p):
        return (design(p[0]) @ p[1:] - y) * w

    res = least_squares(resid, np.r_[f0, coef0], x_scale="jac")
    dof = max(1, len(y) - len(res.x))
    cov = np.linalg.pinv(res.jac.T @ res.jac) * float(np.sum(res.fun**2)) / dof
    f, sf = res.x[0], np.sqrt(max(cov[0, 0], 0.0))
    return float(1 / f), float(sf / f**2)


def _minimum(phase, y, centre, half_width, binned_y):
    """(phase of the lowest smoothed point near centre, depth below maximum light (the highest bin of binned_y),
    width at half depth, the depth's error) of one minimum of a folded curve."""
    d = (phase - centre + 0.5) % 1.0 - 0.5
    near = np.abs(d) <= half_width
    order = np.argsort(d[near])
    x, v = d[near][order], y[near][order]
    k = max(3, len(v) // 25)
    smooth = np.convolve(np.pad(v, k, mode="edge"), np.ones(k) / k, mode="same")[k:-k]  # edges not pulled to 0
    j = int(np.argmin(smooth))
    top = np.nanmax(binned_y)  # maximum light (between W UMa minima there is no flat part)
    bottom = v[np.abs(x - x[j]) <= max(np.ptp(x) / 40, 1e-9)]
    depth = float(top - np.median(bottom))
    below = x[smooth < top - depth / 2]
    width = float(np.ptp(below)) if below.size > 1 else np.nan
    error = float(1.2533 * np.std(bottom) / np.sqrt(max(bottom.size, 1))) if bottom.size > 1 else np.nan
    return float((centre + x[j]) % 1.0), depth, width, error


def eclipses(t, y, period, t0=0.0, half_width=0.15):
    """The two minima of an eclipsing binary folded on period with the primary near phase 0: phases, depths, widths
    (phase units), and e cos ω ≈ π/2 (φ_II − 0.5) (Sterne 1940, small e)."""
    phase = fold(t, period, t0) % 1.0
    y = np.asarray(y, float)
    top = binned(t, y, period, t0)[1]
    p_phase, p_depth, p_width, p_err = _minimum(phase, y, 0.0, half_width, top)
    s_phase, s_depth, s_width, s_err = _minimum(phase, y, (p_phase + 0.5) % 1.0, half_width, top)
    delta = (s_phase - p_phase) % 1.0
    return {"primary_phase": p_phase, "primary_depth": p_depth, "primary_width": p_width, "primary_err": p_err,
            "secondary_phase": s_phase, "secondary_depth": s_depth, "secondary_width": s_width,
            "secondary_err": s_err, "phase_difference": delta, "ecosw": float(np.pi / 2 * (delta - 0.5))}  # fmt: skip


def p_or_2p(t, y, period, t0=0.0, half_width=0.15):
    """Is period the orbital period, or half of it? Folded on 2 × period, the minima at phase 0 and 0.5 are the odd
    and even ones: when their depths differ by more than 3 σ they are a primary and a secondary, and the orbital
    period is 2 × period. {"period": the orbital period, "z": the depth difference in σ, "depths": (odd, even)}."""
    phase = fold(t, 2 * period, t0) % 1.0
    y = np.asarray(y, float)
    top = binned(t, y, 2 * period, t0)[1]
    _, odd, _, e_odd = _minimum(phase, y, 0.0, half_width / 2, top)
    _, even, _, e_even = _minimum(phase, y, 0.5, half_width / 2, top)
    z = abs(odd - even) / np.hypot(e_odd, e_even) if np.isfinite(e_odd) and np.isfinite(e_even) else 0.0
    return {"period": float(2 * period if z > 3 else period), "z": float(z), "depths": (odd, even)}
