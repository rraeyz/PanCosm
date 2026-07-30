"""Integral-field (IFU) data cubes: FITS with two spatial axes and one spectral axis.

The spectral axis is the FITS axis 3 (NAXIS3; numpy axis 0) with a linear or logarithmic WCS
(CRVAL3, CDELT3 or CD3_3, CRPIX3, CTYPE3 *-LOG, CUNIT3 m / um / nm / Angstrom). Images are averages
over a wavelength window; a line map subtracts the continuum interpolated from windows on both sides.
"""

import numpy as np
from astropy.io import fits

UNIT_TO_ANGSTROM = {"m": 1e10, "um": 1e4, "micron": 1e4, "nm": 10.0, "angstrom": 1.0, "a": 1.0, "": 1.0}


def read_cube(path):
    """(data[wave, y, x], wavelengths in Angstrom, header). The data stay memory-mapped (changes never
    reach the file): a cube larger than the RAM works, and images or line maps read only the planes they
    need. Scaled integer cubes (BSCALE/BZERO) cannot be mapped and are read whole."""

    def first_cube(memmap):
        with fits.open(path, memmap=memmap) as hdul:  # the mapping outlives the file object while data is used
            hdu = next((h for h in hdul if h.header.get("NAXIS", 0) == 3), None)
            if hdu is None:
                raise ValueError("no 3-D data cube in this file")
            return hdu.data, hdu.header.copy()

    try:
        data, h = first_cube(True)
    except ValueError as e:
        if "memory-mapped" not in str(e):
            raise
        data, h = first_cube(False)  # BSCALE / BZERO: read whole (astropy cannot map scaled data)
    n = data.shape[0]
    step = h.get("CDELT3", h.get("CD3_3"))
    if step is None or "CRVAL3" not in h:
        raise ValueError("the cube has no wavelength axis (CRVAL3 / CDELT3)")
    pix = np.arange(n) + 1 - h.get("CRPIX3", 1.0)
    wave = h["CRVAL3"] + step * pix
    if str(h.get("CTYPE3", "")).upper().endswith("-LOG"):
        wave = h["CRVAL3"] * np.exp(step * pix / h["CRVAL3"])  # FITS paper III logarithmic axis
    unit = str(h.get("CUNIT3", "")).strip().lower()
    if unit not in UNIT_TO_ANGSTROM:
        raise ValueError(f"unknown wavelength unit {unit}")
    if unit == "" and np.nanmax(wave) < 100:  # bare numbers in microns are common in the infrared
        unit = "um"
    return data, wave * UNIT_TO_ANGSTROM[unit], h


def window(wave, lo, hi):
    sel = (wave >= min(lo, hi)) & (wave <= max(lo, hi))
    if not sel.any():
        sel[np.argmin(np.abs(wave - 0.5 * (lo + hi)))] = True  # narrower than a pixel: the nearest plane
    return sel


def image(data, wave, lo, hi):
    """Mean over the wavelength window [lo, hi] (Angstrom)."""
    with np.errstate(invalid="ignore"):
        return np.nanmean(data[window(wave, lo, hi)], axis=0)


def line_map(data, wave, line, width, gap=None, cont_width=None):
    """Line flux per spaxel: sum over the line window minus a continuum interpolated from windows on
    both sides (each cont_width wide, gap away from the line window). Units: flux x Angstrom."""
    gap = width if gap is None else gap
    cont_width = width if cont_width is None else cont_width
    lw = window(wave, line - width / 2, line + width / 2)
    blue = window(wave, line - width / 2 - gap - cont_width, line - width / 2 - gap)
    red = window(wave, line + width / 2 + gap, line + width / 2 + gap + cont_width)
    with np.errstate(invalid="ignore"):
        cb, cr = np.nanmean(data[blue], axis=0), np.nanmean(data[red], axis=0)
        wb, wr = wave[blue].mean(), wave[red].mean()
    dw = np.gradient(wave)[lw]
    cont = cb[None] + (cr - cb)[None] * ((wave[lw] - wb) / (wr - wb))[:, None, None]
    return np.nansum((data[lw] - cont) * dw[:, None, None], axis=0)


def spaxel_spectrum(data, x, y, radius=1.5):
    """Sum of the spaxels within radius (pixels) of (x, y) (0-based), per wavelength."""
    ny, nx = data.shape[1:]
    yy, xx = np.mgrid[:ny, :nx]
    mask = (xx - x) ** 2 + (yy - y) ** 2 <= radius**2
    if not mask.any():
        mask[int(round(min(max(y, 0), ny - 1))), int(round(min(max(x, 0), nx - 1)))] = True
    return np.nansum(data[:, mask], axis=1)
