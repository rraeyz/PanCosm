"""Time–frequency analysis (plans/period.md PER-9): the weighted wavelet Z-transform of Foster 1996 (AJ 112, 1709)
and a ridge tracer.

At frequency ω (radians per unit of time) and time τ, the data x(t) are projected on 1, cos ω(t − τ),
sin ω(t − τ) with the weights w = exp(−c ω² (t − τ)²) (c sets how many cycles the window spans: about 1/√(2c) / 2π
cycles to each side; Foster's 0.0125 is the usual choice, smaller c sharper in frequency and blurrier in time). With
⟨·⟩ the weighted mean, V_x = ⟨x²⟩ − ⟨x⟩², V_y the variance of the fitted model, and the effective number of points
N_eff = (Σw)² / Σw²:  Z = (N_eff − 3) V_y / (2 (V_x − V_y)), the amplitude √(y₂² + y₃²).
"""

import numpy as np


def wwz(t, x, freqs, taus, c=0.0125, min_points=10):
    """(Z, amplitude, N_eff) on the grid (frequency × time), NaN where N_eff or Σw (points near τ at full weight)
    is below min_points (gaps and edges)."""
    t, x = np.asarray(t, float), np.asarray(x, float)
    x = x - x.mean()
    shape = (len(freqs), len(taus))
    z, amp, neff = np.full(shape, np.nan), np.full(shape, np.nan), np.zeros(shape)
    for i, f in enumerate(freqs):
        om = 2 * np.pi * f
        dt = t[None, :] - np.asarray(taus, float)[:, None]  # (taus, points)
        w = np.exp(-c * om * om * dt * dt)
        sw = w.sum(axis=1)
        n_eff = sw**2 / np.sum(w * w, axis=1)
        neff[i] = n_eff
        p = np.stack([np.ones_like(dt), np.cos(om * dt), np.sin(om * dt)], axis=1)  # (taus, 3, points)
        s = np.einsum("tap,tbp,tp->tab", p, p, w) / sw[:, None, None]
        px = np.einsum("tap,p,tp->ta", p, x, w) / sw[:, None]
        ok = (n_eff >= min_points) & (sw >= min_points)  # N_eff alone ignores scale: far points in a gap count
        if not ok.any():
            continue
        y = np.linalg.solve(s[ok], px[ok][..., None])[..., 0]
        mean_x = (w[ok] @ x) / sw[ok]
        vx = (w[ok] @ (x * x)) / sw[ok] - mean_x**2
        vy = np.sum(y * px[ok], axis=1) - mean_x**2
        z[i, ok] = (n_eff[ok] - 3) * vy / (2 * np.maximum(vx - vy, 1e-300))
        amp[i, ok] = np.hypot(y[:, 1], y[:, 2])
    return z, amp, neff


def ridge(freqs, z):
    """The frequency of the highest Z at each time (parabola through the peak and its neighbours), NaN where the
    column is empty."""
    freqs = np.asarray(freqs, float)
    out = np.full(z.shape[1], np.nan)
    for j in range(z.shape[1]):
        col = z[:, j]
        if not np.isfinite(col).any():
            continue
        k = int(np.nanargmax(col))
        if 0 < k < len(freqs) - 1 and np.all(np.isfinite(col[k - 1 : k + 2])):
            a, b, cc = col[k - 1 : k + 2]
            den = a - 2 * b + cc
            shift = 0.5 * (a - cc) / den if den != 0 else 0.0
            out[j] = freqs[k] + shift * (freqs[k + 1] - freqs[k])
        else:
            out[j] = freqs[k]
    return out
