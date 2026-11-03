"""Long-slit / slitless 2-D spectra: trace, sky subtraction, boxcar and optimal extraction.

Dispersion runs along x (columns), the slit along y. Every function takes plain arrays.

trace:   the spectrum's centre in bins of columns (flux-weighted centroid of the sky-subtracted
         cross-section), then a polynomial fitted with sigma clipping.
boxcar:  sum over +-width/2 around the trace minus the sky (median of two side bands).
optimal: Horne (1986, PASP 98, 609): the spatial profile P (normalised, smoothed along x) and
         per-pixel variance V = (read_noise^2 + max(data,0)/gain) give
         f = sum(P D / V) / sum(P^2 / V),  var(f) = sum(P) / sum(P^2 / V)  with P summing to 1,
         with cosmic-ray rejection of pixels deviating > clip sigma from the profile model.
"""

import numpy as np
from scipy.ndimage import median_filter


def find_spectrum(image) -> float:
    """Row of the brightest spectrum (median across columns)."""
    profile = np.nanmedian(image, axis=1)
    return float(np.nanargmax(profile - np.nanmedian(profile)))


def trace(image, guess_row=None, half_window=10, n_bins=40, order=3, clip=3.0):
    """Return polynomial coefficients y(x) (numpy.polyval order) of the spectrum's centre."""
    ny, nx = image.shape
    guess = find_spectrum(image) if guess_row is None else float(guess_row)
    edges = np.linspace(0, nx, n_bins + 1).astype(int)
    xs, ys = [], []
    for a, b in zip(edges[:-1], edges[1:], strict=True):
        lo, hi = int(max(0, guess - half_window)), int(min(ny, guess + half_window + 1))
        cut = np.nanmedian(image[lo:hi, a:b], axis=1)
        cut = cut - np.nanmedian(cut)
        cut[cut < 0] = 0
        if cut.sum() <= 0:
            continue
        xs.append((a + b - 1) / 2)
        ys.append(lo + np.sum(np.arange(len(cut)) * cut) / cut.sum())
    xs, ys = np.array(xs), np.array(ys)
    keep = np.ones(len(xs), bool)
    for _ in range(5):  # sigma-clipped polynomial
        coef = np.polyfit(xs[keep], ys[keep], min(order, keep.sum() - 1))
        resid = ys - np.polyval(coef, xs)
        new = np.abs(resid) < clip * max(np.std(resid[keep]), 1e-3)
        if np.array_equal(new, keep):
            break
        keep = new
    return coef


def _windows(shape, coef, half_width, sky_offset, sky_width):
    ny, nx = shape
    yc = np.polyval(coef, np.arange(nx))
    y = np.arange(ny)[:, None]
    d = y - yc[None, :]
    obj = np.abs(d) <= half_width
    sky = (np.abs(d) >= sky_offset) & (np.abs(d) <= sky_offset + sky_width)
    return obj, sky


def sky_model(image, coef, half_width, sky_offset, sky_width):
    """Per-column sky level: median of the two side bands (robust to stars and cosmic rays)."""
    _, sky = _windows(image.shape, coef, half_width, sky_offset, sky_width)
    return np.nanmedian(np.where(sky, image, np.nan), axis=0)


def boxcar(image, coef, width=10.0, sky_offset=15.0, sky_width=10.0, subtract_sky=True):
    """Return (flux per column, sky per pixel per column). Arcs fill the slit: subtract_sky=False."""
    obj, _ = _windows(image.shape, coef, width / 2, sky_offset, sky_width)
    if subtract_sky:
        sky = sky_model(image, coef, width / 2, sky_offset, sky_width)
    else:
        sky = np.zeros(image.shape[1])
    flux = np.nansum(np.where(obj, image - sky[None, :], 0.0), axis=0)
    return flux, sky


def optimal(image, coef, width=10.0, sky_offset=15.0, sky_width=10.0, gain=1.0, read_noise=5.0, clip=5.0, smooth=31):
    """Horne optimal extraction. Return (flux, flux_error, sky, rejected-pixel mask)."""
    image = np.asarray(image, float)
    obj, _ = _windows(image.shape, coef, width / 2, sky_offset, sky_width)
    sky = sky_model(image, coef, width / 2, sky_offset, sky_width)
    data = np.where(obj, image - sky[None, :], 0.0)
    box = data.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        prof = np.where(obj, data / box[None, :], 0.0)
    prof = median_filter(np.nan_to_num(prof), size=(1, smooth))  # smooth along the dispersion
    prof = np.clip(prof, 0, None) * obj
    prof /= np.maximum(prof.sum(axis=0, keepdims=True), 1e-12)
    good = obj.copy()
    flux = box
    for _ in range(5):
        var = read_noise**2 / gain**2 + np.clip(flux[None, :] * prof + sky[None, :], 0, None) / gain
        dev = (data - flux[None, :] * prof) ** 2 / var
        bad = good & (dev > clip**2)
        if not bad.any():
            break
        worst = bad & (dev == np.max(np.where(good, dev, -1), axis=0, keepdims=True))  # one pixel per column
        good &= ~worst
        w = np.where(good, prof / var, 0.0)
        flux = np.sum(w * data, axis=0) / np.maximum(np.sum(w * prof, axis=0), 1e-12)
    w = np.where(good, prof / var, 0.0)
    norm = np.maximum(np.sum(w * prof, axis=0), 1e-12)
    flux = np.sum(w * data, axis=0) / norm
    err = np.sqrt(np.sum(np.where(good, prof, 0), axis=0) / norm)
    return flux, err, sky, obj & ~good
