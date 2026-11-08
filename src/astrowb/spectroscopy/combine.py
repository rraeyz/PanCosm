"""Several exposures of one star combined into one spectrum (as IRAF scombine): put on one wavelength grid, scaled to
a common level, outliers (cosmic rays, a hot pixel) rejected pixel by pixel, then averaged, median-combined or summed.

Exposures of one night are combined as they are: the barycentric velocity changes by tens of m/s within a night,
far below a pixel. Spectra of different nights differ by up to ±30 km/s and must be shifted first (or
disentangled), so they are not meant for this.
"""

import warnings

import numpy as np

METHODS = ("mean", "median", "sum")
REJECTIONS = ("none", "sigma", "minmax")


def noise(flux):
    """Pixel noise of a spectrum from its point-to-point scatter (robust, as DER_SNR): for spectra without errors."""
    d = np.diff(np.asarray(flux, float))
    d = d[np.isfinite(d)]
    return 1.4826 * np.median(np.abs(d - np.median(d))) / np.sqrt(2) if d.size > 10 else np.nan


def local_noise(flux, block=200):
    """noise() in blocks along the spectrum, as one value per pixel: an échelle spectrum's S/N changes by a factor of
    two or more from the blaze peaks to the order ends and from blue to red."""
    flux = np.asarray(flux, float)
    edges = np.arange(0, flux.size + block, block)
    centres, values = [], []
    for a, b in zip(edges[:-1], edges[1:], strict=True):
        v = noise(flux[a:b])
        if np.isfinite(v) and v > 0:
            centres.append((a + min(b, flux.size)) / 2)
            values.append(v)
    if not values:
        return np.full(flux.size, noise(flux))
    return np.interp(np.arange(flux.size), centres, values)


def _smooth_ratio(ratio, blocks=40):
    """A ratio of two spectra of one star, smoothed over a fortieth of the range: the continuum shape (chromatic
    losses, airmass) without the lines, which cancel."""
    edges = np.linspace(0, ratio.size, blocks + 1).astype(int)
    centres, values = [], []
    for a, b in zip(edges[:-1], edges[1:], strict=True):
        v = np.nanmedian(ratio[a:b])
        if np.isfinite(v) and v > 0:
            centres.append((a + b) / 2)
            values.append(v)
    return np.interp(np.arange(ratio.size), centres, values) if values else np.ones(ratio.size)


def _block_scatter(resid, block=500):
    """Robust standard deviation of residuals in blocks along the spectrum, one value per pixel."""
    edges = np.arange(0, resid.size + block, block)
    centres, values = [], []
    for a, b in zip(edges[:-1], edges[1:], strict=True):
        r = resid[a:b]
        r = r[np.isfinite(r)]
        if r.size > 20:
            centres.append((a + min(b, resid.size)) / 2)
            values.append(1.4826 * np.median(np.abs(r - np.median(r))))
    return np.interp(np.arange(resid.size), centres, values) if values else np.full(resid.size, np.inf)


def grid(waves):
    """One wavelength grid over all the spectra, as fine as the finest of them."""
    step = min(np.nanmedian(np.diff(np.sort(w))) for w in waves)
    lo, hi = min(np.nanmin(w) for w in waves), max(np.nanmax(w) for w in waves)
    return np.arange(lo, hi + step / 2, step)


def combine(spectra, method="mean", rejection="sigma", sigma=3.0, scale="median", weight="none"):
    """spectra: [(wave, flux, error or None)]. Returns {"wave", "flux", "error", "n" (exposures used per pixel),
    "rejected" (pixels rejected in all), "scales"}. scale: "none", "median" (each to the median level of all) or
    "shape" (to the others' continuum shape as well);
    weight: "none" or "variance" (1/σ², for mean)."""
    with warnings.catch_warnings():  # the grid's ends lie in some exposures only: empty columns are expected
        warnings.simplefilter("ignore", RuntimeWarning)
        return _combine(spectra, method, rejection, sigma, scale, weight)


def _combine(spectra, method, rejection, sigma, scale, weight):
    if method not in METHODS or rejection not in REJECTIONS:
        raise ValueError(f"unknown combine method {method} or rejection {rejection}")
    if len(spectra) < 2:
        raise ValueError("at least two spectra are needed to combine")
    wave = grid([np.asarray(w, float) for w, _, _ in spectra])
    flux, err = [], []
    for w, f, e in spectra:
        w, f = np.asarray(w, float), np.asarray(f, float)
        order = np.argsort(w)
        w, f = w[order], f[order]
        e = np.full(f.shape, np.nan) if e is None else np.asarray(e, float)[order]
        e = np.where(np.isfinite(e) & (e > 0), e, local_noise(f))  # no error given (archive files: NaN)
        inside = (wave >= w[0]) & (wave <= w[-1])
        flux.append(np.where(inside, np.interp(wave, w, f), np.nan))
        err.append(np.where(inside, np.interp(wave, w, e), np.nan))
    flux, err = np.array(flux), np.array(err)
    scales = np.ones(len(spectra))
    if scale == "median":
        common = np.all(np.isfinite(flux), axis=0)  # the level where all of them overlap
        levels = np.array([np.nanmedian(f[common] if common.any() else f) for f in flux])
        scales = np.nanmedian(levels) / levels
        flux, err = flux * scales[:, None], err * scales[:, None]
    elif scale == "shape":  # each to the others' continuum shape too: fibre and slit losses depend on colour
        reference = np.nanmedian(flux, axis=0)
        for i in range(len(flux)):
            smooth = _smooth_ratio(flux[i] / reference)
            flux[i], err[i] = flux[i] / smooth, err[i] / smooth
            scales[i] = 1 / np.nanmedian(smooth)
    good = np.isfinite(flux) & np.isfinite(err)
    n_in = good.sum(axis=0)
    if rejection == "sigma":
        for _ in range(3):  # iterate: a strong outlier pulls the median of few exposures
            centre = np.nanmedian(np.where(good, flux, np.nan), axis=0)
            # the threshold from each exposure's own scatter about the median, in blocks, when larger than its
            # errors: oversampled spectra (HARPS s1d, 0.01 Å) have correlated pixels, and errors from the
            # point-to-point scatter were far too small (two thirds of the pixels of three exposures were rejected)
            spread = np.array(
                [_block_scatter(np.where(g, f - centre, np.nan)) for f, g in zip(flux, good, strict=True)]
            )
            if len(flux) > 1:
                spread *= np.sqrt(len(flux) / (len(flux) - 1))  # the median itself takes part of the scatter
            new = good & (np.abs(flux - centre) <= sigma * np.fmax(err, spread))
            new |= good & (n_in < 3)  # with two exposures the outlier cannot be told from the good one
            if (new == good).all():
                break
            good = new
    elif rejection == "minmax":
        masked = np.where(good, flux, np.nan)
        many = n_in >= 3
        lo, hi = np.nanargmin(np.where(many, masked, 0), axis=0), np.nanargmax(np.where(many, masked, 0), axis=0)
        cols = np.arange(flux.shape[1])
        good[lo[many], cols[many]] = False
        good[hi[many], cols[many]] = False
    n = good.sum(axis=0)
    f, e = np.where(good, flux, np.nan), np.where(good, err, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        if method == "median":
            out = np.nanmedian(f, axis=0)
            out_err = 1.2533 * np.sqrt(np.nansum(e**2, axis=0)) / n  # median of normal noise: √(π/2) × the mean's
        elif method == "sum":
            out = np.nanmean(f, axis=0) * len(spectra)  # a rejected pixel counts as the mean of the others
            out_err = np.sqrt(np.nansum(e**2, axis=0)) / n * len(spectra)
        elif weight == "variance":
            w = 1 / e**2
            out = np.nansum(w * f, axis=0) / np.nansum(w, axis=0)
            out_err = 1 / np.sqrt(np.nansum(w, axis=0))
        else:
            out = np.nanmean(f, axis=0)
            out_err = np.sqrt(np.nansum(e**2, axis=0)) / n
    out[n == 0] = np.nan
    out_err[n == 0] = np.nan
    return {"wave": wave, "flux": out, "error": out_err, "n": n, "rejected": int((n_in - n).sum()), "scales": scales}
