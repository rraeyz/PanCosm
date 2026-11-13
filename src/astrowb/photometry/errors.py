"""Errors that match the scatter (plans/photometry.md PHO-34): the ratio of the observed scatter to the predicted
errors (with the scaling factor offered above 1.2, stored beside the formal errors, never over them), the RMS of
binned residuals against the bin size with the white-noise expectation (the β factor: exoplanets.noise), and the
noise budget of one measurement (photon, sky, read, dark, scintillation)."""

import numpy as np

from ..exoplanets.noise import beta_factor


def scatter_ratio(residuals, errors):
    """Observed RMS over the RMS of the predicted errors; and the factor to offer (None when ≤ 1.2)."""
    r, e = np.asarray(residuals, float), np.asarray(errors, float)
    ratio = float(np.std(r) / np.sqrt(np.mean(e * e)))
    return ratio, (round(ratio, 2) if ratio > 1.2 else None)


def point_to_point_ratio(flux, errors):
    """scatter_ratio on the differences of successive points (σ of a difference is √2 σ): no model needed, and a
    transit or a slow trend barely counts. The standard deviation after one 5σ clip (σ from the MAD): what a χ² sees,
    without one bad point ruling it (the MAD alone left Qatar-1's χ²_r at 1.36 after scaling)."""
    f, e = np.asarray(flux, float), np.asarray(errors, float)
    if f.shape != e.shape:  # a curve without its errors
        return None, None
    ok = np.isfinite(f) & np.isfinite(e) & (e > 0)
    f, e = f[ok], e[ok]
    if len(f) < 10:
        return None, None
    d = np.diff(f)
    mad = 1.4826 * np.median(np.abs(d - np.median(d)))
    observed = np.std(d[np.abs(d - np.median(d)) <= 5 * mad]) / np.sqrt(2)
    ratio = float(observed / np.sqrt(np.mean(e * e)))
    return ratio, (round(ratio, 2) if ratio > 1.2 else None)


def rms_vs_bin(residuals, sizes):
    """[(bin size, RMS of the binned residuals, white-noise expectation σ₁ / √N · √(M / (M − 1)))]."""
    r = np.asarray(residuals, float)
    s1 = np.std(r)
    out = []
    for n in sizes:
        m = len(r) // n
        if m < 3:
            continue
        out.append(
            (n, float(np.std(r[: m * n].reshape(m, n).mean(axis=1))), float(s1 / np.sqrt(n) * np.sqrt(m / (m - 1))))
        )
    return out


def budget(star_e, sky_e_per_px, dark_e_per_px, read_e, pixels, scintillation_rel):
    """The variance of one aperture measurement split by source (electrons²), and the relative total."""
    parts = {"photon": star_e, "sky": pixels * sky_e_per_px, "dark": pixels * dark_e_per_px,
             "read": pixels * read_e**2, "scintillation": (scintillation_rel * star_e) ** 2}  # fmt: skip
    return parts, float(np.sqrt(sum(parts.values())) / star_e)


__all__ = ["beta_factor", "budget", "rms_vs_bin", "scatter_ratio"]
