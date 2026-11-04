"""PSF photometry for crowded fields (plans/photometry.md PHO-18): an empirical PSF (Anderson & King 2000's ePSF,
built by photutils' EPSFBuilder, BSD) from bright isolated stars of the frame, forced photometry of the measured
stars with their catalogue neighbours fitted in the same group (DAOPHOT's nstar idea), and an image with the
neighbours subtracted so that the aperture path can run on it ("aperture after removing neighbours").

Positions are 0-based pixels (x, y). The sky is the frame's sigma-clipped median, subtracted first.
"""

import numpy as np
from astropy.stats import sigma_clipped_stats
from astropy.table import Table


def _sky(data):
    _mean, median, std = sigma_clipped_stats(data, sigma=3.0)
    return median, std


def select_psf_stars(data, xy, fluxes, size=25, n=25, saturation=None, others=None):
    """Indices of up to n stars for the PSF: brightest first, unsaturated, at least `size` px from the edges and
    from any other star (xy plus the optional others)."""
    xy = np.asarray(xy, float).reshape(-1, 2)
    every = xy if others is None else np.vstack([xy, np.asarray(others, float).reshape(-1, 2)])
    ny, nx = data.shape
    half = size / 2 + 2
    out = []
    for i in np.argsort(-np.asarray(fluxes, float)):
        x, y = xy[i]
        if not (half <= x < nx - half and half <= y < ny - half):
            continue
        d = np.hypot(*(every - xy[i]).T)
        if np.any((d > 0.5) & (d < size)):
            continue
        if saturation is not None:
            yi, xi = int(round(y)), int(round(x))
            if data[yi - 2 : yi + 3, xi - 2 : xi + 3].max() >= 0.8 * saturation:
                continue
        out.append(int(i))
        if len(out) == n:
            break
    return out


def build_epsf(data, xy, size=25, oversampling=2):
    """The effective PSF from the stars at xy (an ImagePSF, flux-normalised)."""
    from photutils.psf import EPSFBuilder, extract_stars

    sky, _std = _sky(data)
    from astropy.nddata import NDData

    stars = extract_stars(NDData(data - sky), Table({"x": xy[:, 0], "y": xy[:, 1]}), size=(size, size))
    builder = EPSFBuilder(oversampling=oversampling, maxiters=10, progress_bar=False)
    epsf, _fitted = builder(stars)
    return epsf


def gaussian(fwhm):
    from photutils.psf import CircularGaussianPRF

    return CircularGaussianPRF(fwhm=fwhm)


def measure(data, psf, xy, fwhm, neighbours=(), fit_positions=False, max_move=1.0, fit_size=None):
    """Flux and error of the stars at xy, fitted together with their neighbours in groups (separation 2.5 FWHM).
    Returns (flux, flux_err, table) — the arrays for xy only; the table holds every fitted star (xy first)."""
    from photutils.psf import PSFPhotometry, SourceGrouper

    sky, std = _sky(data)
    stars = np.vstack([np.asarray(xy, float).reshape(-1, 2), np.asarray(neighbours, float).reshape(-1, 2)])
    model = psf.copy()
    model.x_0.fixed = model.y_0.fixed = not fit_positions
    size = fit_size or int(2 * round(1.5 * fwhm) + 1)
    phot = PSFPhotometry(model, (size, size), grouper=SourceGrouper(2.5 * fwhm), aperture_radius=1.5 * fwhm,
                         xy_bounds=max_move if fit_positions else None)  # fmt: skip
    init = Table({"x": stars[:, 0], "y": stars[:, 1]})
    table = phot(data - sky, error=np.full(data.shape, std), init_params=init)
    n = len(np.asarray(xy).reshape(-1, 2))
    return np.asarray(table["flux_fit"][:n]), np.asarray(table["flux_err"][:n]), table


def subtract(data, psf, table, rows):
    """data with the fitted stars of the given table rows subtracted."""
    out = np.array(data, float)
    yy, xx = np.indices(data.shape)
    for r in rows:
        m = psf.copy()
        m.x_0, m.y_0, m.flux = table["x_fit"][r], table["y_fit"][r], table["flux_fit"][r]
        out -= m(xx, yy)
    return out


def neighbours_of(data, stars, fwhm, r_out, find):
    """Stars that are not measured stars but lie within r_out + 2 FWHM of one (their light falls in an aperture or a
    sky ring): found by find(image) on the frame with the measured stars fitted and subtracted (DAOPHOT's way: a
    neighbour blended with a brighter star shows only in the residuals)."""
    stars = np.asarray(stars, float).reshape(-1, 2)
    model = gaussian(fwhm)
    _f, _e, table = measure(data, model, stars, fwhm, fit_positions=True)
    residual = subtract(data, model, table, range(len(stars)))
    detected = np.vstack([np.asarray(find(img), float).reshape(-1, 2) for img in (data, residual)])
    if not len(detected):
        return detected
    d = np.hypot(*(detected[:, None, :] - stars[None, :, :]).transpose(2, 0, 1)).min(axis=1)
    near = detected[(d > 1.0 * fwhm) & (d < r_out + 2 * fwhm)]  # closer: the residual of a measured star itself
    keep = []  # the same star found in both images
    for p in near:
        if all(np.hypot(*(p - q)) > 0.7 * fwhm for q in keep):
            keep.append(p)
    return np.array(keep).reshape(-1, 2)


def neighbours_setup(ref, stars0, n_comp, r_out):
    """(neighbours, stars0) for remove_neighbours, from the reference frame (light_curve's remove_neighbours)."""
    from .aperture import seeing_fwhm
    from .fieldstars import detect_stars

    f_ref = seeing_fwhm(ref, stars0[: 1 + n_comp])
    f_ref = f_ref if np.isfinite(f_ref) else 3.0
    return neighbours_of(ref, stars0, f_ref, r_out, lambda img: detect_stars(img, 500, f_ref, 5)), stars0


def remove_neighbours(data, xy, fwhm, neighbours, stars0):
    """data with the neighbours (positions on the reference frame, moved by this frame's median shift of the
    measured stars xy from stars0) fitted together with the measured stars and subtracted.
    shortcut: a circular Gaussian of the frame's FWHM, not the ePSF; build an ePSF per frame if the residuals show."""
    neighbours = np.asarray(neighbours, float).reshape(-1, 2)
    if not len(neighbours) or not np.isfinite(fwhm):
        return data
    shift = np.median(np.asarray(xy, float) - np.asarray(stars0, float), axis=0)
    model = gaussian(fwhm)
    _f, _e, table = measure(data, model, xy, fwhm, neighbours=neighbours + shift, fit_positions=True)
    n = len(np.asarray(xy).reshape(-1, 2))
    return subtract(data, model, table, range(n, len(table)))
