"""The shape of a folded light curve (plans/period.md PER-10): the Fourier decomposition of Simon & Lee 1981,

    y(φ) = A₀ + Σ_k A_k sin(2π k φ + φ_k),   R_k1 = A_k / A₁,   φ_k1 = φ_k − k φ₁ (mod 2π),

its order chosen by BIC, every parameter with its error propagated from the fit's covariance; the rise time (from
minimum to maximum light) and the skewness of the curve. Magnitudes: maximum light is the smallest value.
"""

import numpy as np


def _design(phase, order):
    cols = [np.ones_like(phase)]
    for k in range(1, order + 1):
        cols += [np.sin(2 * np.pi * k * phase), np.cos(2 * np.pi * k * phase)]
    return np.column_stack(cols)


def decompose(phase, y, err=None, max_order=10, order=None):
    """{"order", "A0", "A" (k = 1 …), "phi" (radians), "R" {k: (R_k1, error)}, "phi_k1" {k: (value, error)},
    "coef", "cov", "rms"}."""
    phase, y = np.asarray(phase, float) % 1.0, np.asarray(y, float)
    w = np.ones_like(y) if err is None else 1 / np.asarray(err, float)
    best = None
    for k in [order] if order else range(1, max_order + 1):
        a = _design(phase, k) * w[:, None]
        coef, *_ = np.linalg.lstsq(a, y * w, rcond=None)
        r = y * w - a @ coef
        n = len(y)
        bic = n * np.log(np.mean(r * r)) + (2 * k + 1) * np.log(n)
        if best is None or bic < best[0]:
            best = (bic, k, coef, a, r)
    _bic, k, coef, a, r = best
    cov = np.linalg.inv(a.T @ a) * (r @ r / max(len(y) - len(coef), 1)) if err is None else np.linalg.inv(a.T @ a)
    s, c = coef[1::2], coef[2::2]  # sin and cos coefficients: A sin(x + φ) = A cos φ sin x + A sin φ cos x
    amp, phi = np.hypot(s, c), np.arctan2(c, s)
    # Jacobian of (A_k, φ_k) for all k with respect to the coefficients, for the propagation
    jac = np.zeros((2 * k, len(coef)))
    for i in range(k):
        jac[i, 1 + 2 * i], jac[i, 2 + 2 * i] = s[i] / amp[i], c[i] / amp[i]
        jac[k + i, 1 + 2 * i], jac[k + i, 2 + 2 * i] = -c[i] / amp[i] ** 2, s[i] / amp[i] ** 2
    v = jac @ cov @ jac.T
    out = {"order": k, "A0": float(coef[0]), "A": amp, "phi": phi, "R": {}, "phi_k1": {}, "coef": coef, "cov": cov,
           "rms": float(np.sqrt(np.mean((r / w) ** 2)))}  # fmt: skip
    for j in range(2, k + 1):
        i = j - 1
        ratio = amp[i] / amp[0]
        g = np.zeros(2 * k)
        g[i], g[0] = 1 / amp[0], -amp[i] / amp[0] ** 2
        out["R"][j] = (float(ratio), float(np.sqrt(g @ v @ g)))
        h = np.zeros(2 * k)
        h[k + i], h[k] = 1.0, -float(j)
        out["phi_k1"][j] = (float((phi[i] - j * phi[0]) % (2 * np.pi)), float(np.sqrt(h @ v @ h)))
    return out


def curve(d, phase):
    return _design(np.asarray(phase, float) % 1.0, d["order"]) @ d["coef"]


def rise_time(d, magnitudes=True, n=20000):
    """The phase interval from minimum to maximum light of the fitted curve (0 … 1)."""
    ph = np.arange(n) / n
    y = curve(d, ph)
    bright = y if not magnitudes else -y
    return float((ph[np.argmax(bright)] - ph[np.argmin(bright)]) % 1.0)


def skewness(d, magnitudes=True, n=20000):
    """The skewness of the fitted curve's values over phase (brightness made positive for magnitudes)."""
    y = curve(d, np.arange(n) / n)
    y = -y if magnitudes else y
    z = (y - y.mean()) / y.std()
    return float(np.mean(z**3))
