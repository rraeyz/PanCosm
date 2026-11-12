"""Starting values from the data (plans/models.md MOD-11): the folded light curve described by the two-Gaussian
model of Mowlavi et al. 2017 (A&A 606, A92) — a constant, an ellipsoidal cosine and one Gaussian per eclipse,
wrapped in phase — and the classical relations from its eclipses to the elements:

    e cos ω ≈ (π/2) (Δφ − 1/2)                  (the secondary's displacement; Δφ the separation of the eclipses)
    e sin ω ≈ (w₂ − w₁) / (w₂ + w₁)             (the widths: the eclipse nearer apastron lasts longer)
    r₁ + r₂ ≈ π W / (1 − e sin ω …)             (W the full width of an eclipse in phase, from the Gaussian's σ)
    J ≈ d₂ / d₁                                  (the depths: surface-brightness ratio, circular, i ≈ 90°)

Each estimate comes with how it was found; they start a fit, they are not results.
"""

import numpy as np
from scipy.optimize import least_squares

SIGMA_TO_DURATION = 5.0  # full eclipse width ≈ this × the fitted Gaussian's σ (calibrated on models.eb curves)


def _wrapped(phase, mu, sigma):
    d = (phase - mu + 0.5) % 1.0 - 0.5
    return np.exp(-0.5 * (d / sigma) ** 2)


def two_gaussian(phase, p):
    c, ell, d1, mu1, s1, d2, mu2, s2 = p
    return c + ell * np.cos(4 * np.pi * (phase - mu1)) - d1 * _wrapped(phase, mu1, s1) - d2 * _wrapped(phase, mu2, s2)


def fit_two_gaussian(phase, flux):
    """The model's parameters (c, ellipsoidal amplitude, depth₁, μ₁, σ₁, depth₂, μ₂, σ₂) and the rms; eclipse 1
    the deeper, started at the lowest binned point and half a cycle on."""
    phase, flux = np.asarray(phase, float) % 1.0, np.asarray(flux, float)
    bins = np.linspace(0, 1, 101)
    idx = np.digitize(phase, bins) - 1
    med = np.array([np.median(flux[idx == k]) if np.any(idx == k) else np.nan for k in range(100)])
    k = int(np.nanargmin(med))
    mu1 = (k + 0.5) / 100
    top = np.nanpercentile(med, 90)
    starts = []
    for shift in (0.5, 0.45, 0.55, 0.4, 0.6):
        mu2 = (mu1 + shift) % 1
        d2 = max(top - med[int(mu2 * 100) % 100], 1e-4) if np.isfinite(med[int(mu2 * 100) % 100]) else 1e-3
        starts.append([top, 0.0, top - med[k], mu1, 0.03, d2, mu2, 0.03])
    lo = [-np.inf, -np.inf, 0, -np.inf, 1e-3, 0, -np.inf, 1e-3]
    hi = [np.inf, np.inf, np.inf, np.inf, 0.25, np.inf, np.inf, 0.25]
    best = min((least_squares(lambda p: two_gaussian(phase, p) - flux, s, bounds=(lo, hi)) for s in starts),
               key=lambda r: r.cost)  # fmt: skip
    p = best.x.copy()
    if p[5] > p[2]:  # eclipse 1 the deeper
        p[2:5], p[5:8] = p[5:8].copy(), p[2:5].copy()
    p[3] %= 1.0
    p[6] %= 1.0
    return p, float(np.sqrt(np.mean(best.fun**2)))


def estimate(phase, flux):
    """{"ecosw", "esinw", "r_sum", "j", "morphology", "spot", each with (value, how)} and the model's parameters."""
    p, rms = fit_two_gaussian(phase, flux)
    c, ell, d1, mu1, s1, d2, mu2, s2 = p
    dphi = (mu2 - mu1) % 1.0
    ecosw = np.pi / 2 * (dphi - 0.5)
    esinw = (s2 - s1) / (s2 + s1)
    width = SIGMA_TO_DURATION * 0.5 * (s1 + s2)
    r_sum = np.pi * width
    j = d2 / d1 if d1 > 0 else np.nan
    rel_ell = abs(ell) / c
    if r_sum > 0.75 or (rel_ell > 0.03 and abs(d1 - d2) / max(d1, 1e-9) < 0.3):
        morph = ("contact", "wide eclipses and a strongly curved maximum")
    elif rel_ell > 0.01:
        morph = ("semi-detached", "curved maxima: distorted stars")
    else:
        morph = ("detached", "flat outside the eclipses")
    out = {"ecosw": (ecosw, "from the secondary's phase"), "esinw": (esinw, "from the eclipse widths"),
           "r_sum": (r_sum, "from the eclipse widths"), "j": (j, "from the depth ratio"), "morphology": morph,
           "model": p, "rms": rms}  # fmt: skip
    return out


def oconnell(phase, flux, mu1):
    """The difference of the maxima (at the quadratures after the primary): a spot is suggested beyond 3 σ."""
    phase, flux = np.asarray(phase, float) % 1.0, np.asarray(flux, float)
    a = np.abs((phase - mu1 - 0.25 + 0.5) % 1 - 0.5) < 0.05
    b = np.abs((phase - mu1 - 0.75 + 0.5) % 1 - 0.5) < 0.05
    diff = np.mean(flux[a]) - np.mean(flux[b])
    err = np.hypot(np.std(flux[a]) / np.sqrt(a.sum()), np.std(flux[b]) / np.sqrt(b.sum()))
    return float(diff), float(err), bool(abs(diff) > 3 * err)
