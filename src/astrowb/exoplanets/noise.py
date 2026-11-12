"""Noise that is not white, the simple treatments (plans/exoplanets.md EXO-13): the β factor of the time-averaging
method (Pont et al. 2006; Winn et al. 2008, ApJ 683, 1076) and the error scaling to χ²ᵣ = 1. Residuals binned in
groups of N points scatter as σ_N; white noise gives σ₁ / √N · √(M / (M − 1)) (M bins); β is the ratio of the
measured to that expectation, taken as the median over bin sizes around the time scale of interest (an ingress)."""

import numpy as np


def beta_factor(residuals, sizes):
    """β = median over the bin sizes N (points per bin) of σ_N / (σ₁ / √N · √(M / (M − 1))), at least 1."""
    r = np.asarray(residuals, float)
    s1 = np.std(r)
    ratios = []
    for n in sizes:
        m = len(r) // n
        if m < 3:
            continue
        means = r[: m * n].reshape(m, n).mean(axis=1)
        ratios.append(np.std(means) / (s1 / np.sqrt(n) * np.sqrt(m / (m - 1))))
    return max(float(np.median(ratios)), 1.0) if ratios else 1.0


def scale_to_chi2(residuals, errors, n_params):
    """The factor that makes χ²ᵣ of the residuals 1 (never below 1)."""
    r, e = np.asarray(residuals, float), np.asarray(errors, float)
    return max(float(np.sqrt(np.sum((r / e) ** 2) / max(len(r) - n_params, 1))), 1.0)
