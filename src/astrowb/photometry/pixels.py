"""Tools for space-mission pixel files (TESS, Kepler, K2; plans/photometry.md PHO-32), on a cube (cadences, ny, nx):

    mask = threshold_mask(cube, 3.0)            the target's pixels: brighter than the stamp's median by n robust σ,
                                                the connected group holding the brightest pixel (lightkurve's idea)
    bkg = background(cube, mask)                per cadence, the median of the faintest pixels outside the mask
    flux = sap(cube, mask, bkg)                 simple aperture photometry
    flat = pld(cube, mask, flux, exclude)       pixel-level decorrelation (Deming et al. 2015; Luger et al. 2016):
                                                the flux fitted by the aperture's pixel fractions (principal
                                                components of them), the transit / eclipse frames left out of the fit
    shift = centroid_shift(cube, mask, in_t)    the flux-weighted centroid in transit minus out of it, with its
                                                error: a blended eclipsing star moves the centroid

The algorithms are reimplemented from their papers and lightkurve's description (MIT), not copied.
"""

import numpy as np
from scipy import ndimage


def threshold_mask(cube, nsigma=3.0, reference=None):
    img = np.nanmedian(np.asarray(cube, float), axis=0)
    med = np.nanmedian(img)
    mad = 1.4826 * np.nanmedian(np.abs(img - med))
    above = img > med + nsigma * mad
    labels, _ = ndimage.label(above)
    if reference is None:
        reference = np.unravel_index(np.nanargmax(np.where(above, img, -np.inf)), img.shape)
    keep = labels[reference]
    return labels == keep if keep else above


def background(cube, mask, fraction=0.3):
    """Per cadence: the median of the faintest pixels (by the stamp's median image) outside the mask."""
    cube = np.asarray(cube, float)
    img = np.nanmedian(cube, axis=0)
    out = ~ndimage.binary_dilation(mask, iterations=1)
    level = np.nanpercentile(img[out], 100 * fraction)
    faint = out & (img <= level)
    return np.nanmedian(cube[:, faint], axis=1)


def sap(cube, mask, bkg=None):
    cube = np.asarray(cube, float)
    total = cube[:, mask].sum(axis=1)
    return total if bkg is None else total - np.asarray(bkg, float) * mask.sum()


def pld(cube, mask, flux, exclude=None, n_components=8, bkg=None, order=2):
    """The flux with the pointing's systematics removed: regressed on the leading principal components of the
    aperture pixels' fractional fluxes (first-order PLD) and, with order 2, the products of the leading few (a
    centred star loses light as the square of its offset), plus a constant, fitted outside `exclude` (bool per
    cadence); the signal's own frames are left out so a transit keeps its depth. Returns the corrected flux at the
    same median level."""
    cube = np.asarray(cube, float)
    pix = cube[:, mask] - (0.0 if bkg is None else np.asarray(bkg, float)[:, None])
    frac = pix / pix.sum(axis=1, keepdims=True)
    frac = frac - frac.mean(axis=0)
    u, s, _ = np.linalg.svd(frac, full_matrices=False)
    comps = u[:, :n_components]
    cols = [np.ones(len(flux)), *comps.T]
    if order >= 2:
        lead = comps[:, : min(4, comps.shape[1])]
        cols += [lead[:, i] * lead[:, j] for i in range(lead.shape[1]) for j in range(i, lead.shape[1])]
    basis = np.column_stack(cols)
    flux = np.asarray(flux, float)
    fit = np.ones(len(flux), bool) if exclude is None else ~np.asarray(exclude, bool)
    fit &= np.isfinite(flux)
    coef, *_ = np.linalg.lstsq(basis[fit], flux[fit], rcond=None)
    trend = basis @ coef
    return flux - trend + np.nanmedian(flux[fit])


def centroids(cube, mask, bkg=None):
    """Flux-weighted centroid (x, y) per cadence within the mask."""
    cube = np.asarray(cube, float)
    w = np.where(mask, cube - (0.0 if bkg is None else np.asarray(bkg, float)[:, None, None]), 0.0)
    yy, xx = np.indices(mask.shape)
    total = w.sum(axis=(1, 2))
    return (w * xx).sum(axis=(1, 2)) / total, (w * yy).sum(axis=(1, 2)) / total


def centroid_shift(cube, mask, in_transit, bkg=None):
    """{"dx", "dy", "shift", "error", "significance"}: the mean centroid in transit minus out of it (pixels)."""
    x, y = centroids(cube, mask, bkg)
    it = np.asarray(in_transit, bool)
    out = {}
    for name, c in (("dx", x), ("dy", y)):
        a, b = c[it], c[~it]
        out[name] = float(a.mean() - b.mean())
        out[name + "_err"] = float(np.hypot(a.std(ddof=1) / np.sqrt(len(a)), b.std(ddof=1) / np.sqrt(len(b))))
    shift = float(np.hypot(out["dx"], out["dy"]))
    err = float(np.hypot(out["dx"] * out["dx_err"], out["dy"] * out["dy_err"]) / shift) if shift else float("nan")
    return out | {"shift": shift, "error": err, "significance": shift / err if err else float("nan")}
