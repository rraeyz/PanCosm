"""Template library and spectral-type estimate.

Library: any folder of spectra whose spectral type is in the header (SPTYPE, or Pickles' "spectral type: …"
comment) or the file name. The Pickles (1998, PASP 110, 863) library of 131 stars, O5 to M6, all luminosity
classes, 1150-25000 A at ~5 A resolution, is downloaded from STScI on first use (it is not bundled).

Estimate: observed spectra are not flux-calibrated (the instrument response tilts them), so both spectra are
divided by their own smooth continuum and the line pattern is compared: the template is smoothed to the
observed resolution, resampled, and ranked by the rms difference (telluric bands left out).
"""

import re
from pathlib import Path

import numpy as np

PICKLES_URL = "https://ssb.stsci.edu/cdbs/grid/pickles/dat_uvk/pickles_uk_{i}.fits"
PICKLES_N = 131
TELLURIC = ((6860, 6960), (7590, 7700), (8100, 8400), (8900, 9900))


def download_pickles(folder, fetch=None):
    """The Pickles library into folder (skips files already there); returns the paths."""
    import urllib.request

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    fetch = fetch or (lambda url: urllib.request.urlopen(url, timeout=60).read())
    paths = []
    for i in range(1, PICKLES_N + 1):
        p = folder / f"pickles_uk_{i}.fits"
        if not p.exists():
            data = fetch(PICKLES_URL.format(i=i))
            tmp = p.with_suffix(".part")
            tmp.write_bytes(data)
            tmp.replace(p)  # never a half-written template
        paths.append(p)
    return paths


def read_template(path):
    """(wave, flux, spectral type) of a library spectrum."""
    from astropy.io import fits

    from . import spectrum_io

    path = Path(path)
    with fits.open(path) as hdul:
        head = hdul[0].header
        text = " ".join(str(head.get(k, "")) for k in ("SPTYPE", "COMMENT1"))
        if len(hdul) > 1 and hasattr(hdul[1], "columns") and "WAVELENGTH" in hdul[1].columns.names:  # Pickles
            wave, flux = np.asarray(hdul[1].data["WAVELENGTH"], float), np.asarray(hdul[1].data["FLUX"], float)
        else:
            wave, flux, _, _ = spectrum_io.read(path)
    m = re.search(r"spectral type:\s*(\S+)", text) or re.search(r"\b([OBAFGKM]\d(?:\.\d)?\s*(?:I{1,3}|IV|V)\S*)", text)
    sptype = m.group(1) if m else (str(head.get("SPTYPE", "")).strip() or path.stem)
    return np.asarray(wave, float), np.asarray(flux, float), sptype


def _normalise(wave, flux, order=5):
    from .rv import continuum_normalise

    return continuum_normalise(wave, flux, order=order)


def classify(wave, flux, library, fwhm=None, top=5):
    """[(spectral type, rms, path)] best first. fwhm: resolution of the observed spectrum in A (default:
    two pixels, at least the library's 5 A)."""
    from scipy.ndimage import gaussian_filter1d

    wave, flux = np.asarray(wave, float), np.asarray(flux, float)
    ok = np.isfinite(wave) & np.isfinite(flux)
    wave, flux = wave[ok], flux[ok]
    step = float(np.median(np.diff(wave)))
    fwhm = fwhm or max(5.0, 2 * step)
    keep = np.ones(len(wave), bool)
    for lo, hi in TELLURIC:
        keep &= ~((wave > lo) & (wave < hi))
    obs = _normalise(wave, flux)
    out = []
    for path in library:
        tw, tf, sptype = read_template(path)
        good = np.isfinite(tf) & (tf > 0)
        tw, tf = tw[good], tf[good]
        sel = (tw > wave[0] - 50) & (tw < wave[-1] + 50)
        if sel.sum() < 20:
            continue
        tw, tf = tw[sel], tf[sel]
        grid = np.arange(tw[0], tw[-1], min(step, float(np.median(np.diff(tw)))))
        tg = np.interp(grid, tw, tf)
        sigma = max(fwhm**2 - 5.0**2, 0.0) ** 0.5 / 2.355 / (grid[1] - grid[0])  # on top of the library's 5 A
        if sigma > 0.3:
            tg = gaussian_filter1d(tg, sigma)
        t = _normalise(wave, np.interp(wave, grid, tg))
        rms = float(np.sqrt(np.nanmean((obs[keep] - t[keep]) ** 2)))
        out.append((sptype, rms, str(path)))
    out.sort(key=lambda r: r[1])
    return out[:top]
