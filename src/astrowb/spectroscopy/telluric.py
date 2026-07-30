"""Telluric correction with a telluric standard (a hot, fast-rotating star observed near the target).

The standard's continuum-normalised spectrum is the atmospheric transmission T at its airmass.
For the science spectrum the absorption scales as optical depth: T_sci = T ** s (s ~ airmass ratio,
fitted because water vapour changes too), and the two wavelength scales may differ by a fraction
of a pixel, so the shift is fitted as well. Both are found inside the telluric bands only:
    s     = sum(ln F ln T) / sum(ln T ^ 2)  over pixels with real absorption (F the normalised science)
    shift = the one that minimises the scatter of F / T**s in the bands (scanned, then parabola)
The science spectrum is divided by T**s; pixels where T**s < min_transmission are flagged
(little light left: the correction would only amplify noise).
"""

import numpy as np

from .rv import C_KMS, continuum_normalise

# main telluric absorption bands in the optical/near-IR (Angstrom, air)
BANDS = [(5880, 5990), (6270, 6330), (6860, 6950), (7160, 7340), (7590, 7700), (8120, 8350), (8950, 9800)]


def _in_bands(wave, bands):
    m = np.zeros(len(wave), bool)
    for lo, hi in bands:
        m |= (wave >= lo) & (wave <= hi)
    return m


def transmission(std_wave, std_flux, order=3):
    """Telluric transmission from the standard: its continuum-normalised spectrum, capped at 1."""
    return np.clip(continuum_normalise(std_wave, std_flux, order), 1e-3, 1.0)


def correct(wave, flux, std_wave, std_flux, bands=BANDS, max_shift_kms=15.0, min_transmission=0.2, order=3):
    """Return dict(flux, transmission, power, shift_kms, bad). flux keeps the science spectrum's
    continuum (only the telluric lines are divided out)."""
    wave, flux = np.asarray(wave, float), np.asarray(flux, float)
    if _in_bands(wave, bands).sum() < 20:
        raise ValueError("the spectrum does not cover a telluric band")
    t_std = transmission(std_wave, std_flux, order)
    ln_std = np.log(np.asarray(std_wave, float))
    cont = flux / continuum_normalise(wave, flux, order)
    norm = flux / cont
    sel = _in_bands(wave, bands) & np.isfinite(norm) & (norm > 0)
    if sel.sum() < 20:
        raise ValueError("the spectrum does not cover a telluric band")
    v_pix = C_KMS * np.median(np.diff(np.log(wave)))

    def model_t(v):
        return np.interp(np.log(wave) - v / C_KMS, ln_std, t_std, left=1.0, right=1.0)

    def power(t):
        use = sel & (t < 0.98)
        if use.sum() < 5:
            return 1.0
        lt = np.log(t[use])
        return float(np.sum(np.log(norm[use]) * lt) / np.sum(lt * lt))

    def scatter(v):
        t = model_t(v)
        return float(np.std((norm / t ** power(t))[sel]))

    step = 0.1 * v_pix
    shifts = np.arange(-max_shift_kms, max_shift_kms + step / 2, step)
    sc = np.array([scatter(v) for v in shifts])
    j = int(np.argmin(sc))
    v = shifts[j]
    if 0 < j < len(sc) - 1:
        den = sc[j - 1] - 2 * sc[j] + sc[j + 1]
        if den > 0:
            v += 0.5 * (sc[j - 1] - sc[j + 1]) / den * step
    t = model_t(v)
    s = power(t)
    ts = t**s
    return {
        "flux": flux / ts,
        "transmission": ts,
        "power": s,
        "shift_kms": float(v),
        "bad": ts < min_transmission,
    }
