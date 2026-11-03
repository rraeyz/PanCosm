"""Seismology basics for solar-like oscillators (plans/period.md PER-14), after Huber et al. 2009's pipeline:
the power density spectrum, the granulation background divided out by a wide running median in log frequency,
νmax as the peak of the heavily smoothed excess, Δν from the autocorrelation of the spectrum around νmax (searched
near Stello et al. 2009's Δν ≈ 0.263 νmax^0.772), and the scaling relations (Kjeldsen & Bedding 1995) with Huber
et al. 2011's solar values νmax☉ = 3090 µHz, Δν☉ = 135.1 µHz, Teff☉ = 5777 K.

Times in days; flux relative (1 = mean); frequencies in µHz.
"""

import numpy as np

NUMAX_SUN, DNU_SUN, TEFF_SUN = 3090.0, 135.1, 5777.0


def psd(t, flux, f_max=None, oversample=1):
    """(frequencies µHz, power density ppm² / µHz), normalised so that the integral is the variance (Parseval)."""
    from astropy.timeseries import LombScargle

    t_s = (np.asarray(t, float) - np.min(t)) * 86400
    y = (np.asarray(flux, float) / np.mean(flux) - 1) * 1e6
    nyq = 0.5 / np.median(np.diff(np.sort(t_s))) * 1e6
    df = 1e6 / np.ptp(t_s) / oversample
    f = np.arange(df, (f_max or nyq) + df, df)
    p = LombScargle(t_s, y, normalization="psd").power(f * 1e-6)
    # astropy's psd: power = 0.5 · (fit amplitude² · N / 2)…; scale to Parseval: Σ P df = variance
    p = p * np.var(y) / np.sum(p * df)
    return f, p


def _running_median_log(f, p, width_dex):
    lf = np.log10(f)
    out = np.empty_like(p)
    for i, x in enumerate(lf):
        sel = np.abs(lf - x) < width_dex / 2
        out[i] = np.median(p[sel])
    return out


def numax(f, p, f_min=None, f_max=None, background_dex=0.4):
    """νmax: the peak of the background-divided spectrum smoothed by a Gaussian of a quarter of the expected Δν
    envelope (here 0.07 dex in frequency)."""
    from scipy.ndimage import gaussian_filter1d

    bg = _running_median_log(f, p, background_dex)
    snr = p / bg
    sel = np.ones_like(f, bool) if f_min is None else (f >= f_min) & (f <= (f_max or f.max()))
    sigma_pts = max(int(0.07 * np.median(f[sel]) / np.median(np.diff(f))), 1)
    smooth = gaussian_filter1d(snr, sigma_pts)
    return float(f[sel][int(np.argmax(smooth[sel]))])


def dnu(f, p, nu_max, background_dex=0.4):
    """Δν from the autocorrelation of the background-divided spectrum within νmax ± 0.25 νmax, the highest peak
    within a factor 1.5 of Stello et al.'s expectation, refined by a parabola."""
    bg = _running_median_log(f, p, background_dex)
    sel = np.abs(f - nu_max) < 0.25 * nu_max
    x = p[sel] / bg[sel] - 1
    step = np.median(np.diff(f))
    n = x.size
    ac = np.correlate(x, x, "full")[n - 1 :] / np.arange(n, 0, -1)
    lags = np.arange(n) * step
    guess = 0.263 * nu_max**0.772
    window = (lags > guess / 1.5) & (lags < guess * 1.5)
    k = int(np.flatnonzero(window)[np.argmax(ac[window])])
    a, b, c = ac[k - 1 : k + 2]
    shift = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
    return float((k + shift) * step)


def scaling(nu_max, delta_nu, teff):
    """(M, R) in solar units from the scaling relations."""
    m = (nu_max / NUMAX_SUN) ** 3 * (delta_nu / DNU_SUN) ** -4 * (teff / TEFF_SUN) ** 1.5
    r = (nu_max / NUMAX_SUN) * (delta_nu / DNU_SUN) ** -2 * (teff / TEFF_SUN) ** 0.5
    return float(m), float(r)
