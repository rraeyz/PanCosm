"""Long-slit / slitless 2-D spectra: trace, sky subtraction, boxcar and optimal extraction.

Dispersion runs along x (columns), the slit along y. Every function takes plain arrays.

trace:   as IRAF apextract's aptrace: from a starting column the spectrum is followed in steps of `step`
         columns (sums of `nsum` columns), each centre found near the previous one (flux-weighted centroid of
         the background-subtracted cross-section within `half_window`), the trace given up after `nlost`
         steps in a row without a clear signal; then a polynomial fitted with sigma clipping.
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


def trace(image, guess_row=None, half_window=10, step=10, nsum=10, nlost=3, order=3, clip=3.0):
    """Return polynomial coefficients y(x) (numpy.polyval order) of the spectrum's centre.
    guess_row: a row the spectrum crosses (the user's choice when several spectra are on the frame); default:
    the brightest spectrum. Tracing starts at the column where it is brightest and goes both ways."""
    ny, nx = image.shape
    cols = np.arange(0, nx - nsum + 1, step)

    def cut(c):  # the cross-section at column c: nsum columns, background (median) taken off
        v = np.nanmedian(image[:, c : c + nsum], axis=1)
        return v - np.nanmedian(v)

    if guess_row is None:
        peaks = [np.nanmax(cut(c)) for c in cols]
        k0 = int(np.nanargmax(peaks))  # the column where the spectrum is brightest
        y0 = float(np.nanargmax(cut(cols[k0])))
    else:
        lo, hi = int(max(0, guess_row - half_window)), int(min(ny, guess_row + half_window + 1))
        k0 = int(np.nanargmax([np.nanmax(cut(c)[lo:hi]) for c in cols]))
        y0 = lo + float(np.nanargmax(cut(cols[k0])[lo:hi]))

    def centre(c, y):
        v = cut(c)
        noise = 1.4826 * np.nanmedian(np.abs(v - np.nanmedian(v)))
        lo, hi = int(max(0, round(y) - half_window)), int(min(ny, round(y) + half_window + 1))
        w = np.clip(v[lo:hi], 0, None)
        if hi - lo < 3 or np.nanmax(w) < 5 * max(noise, 1e-9):
            return None  # no clear signal here
        return lo + float(np.sum(np.arange(hi - lo) * w) / np.sum(w))

    xs, ys = [], []
    for direction in (range(k0, len(cols)), range(k0 - 1, -1, -1)):
        y, lost = y0, 0
        for k in direction:
            new = centre(cols[k], y)
            if new is None or abs(new - y) > half_window:
                lost += 1
                if lost >= nlost:
                    break  # lost: the rest of this side is left to the polynomial
                continue
            lost, y = 0, new
            xs.append(cols[k] + (nsum - 1) / 2)
            ys.append(y)
    if len(xs) < order + 2:
        raise ValueError(
            "the spectrum could not be followed: for a faint one, give a brighter spectrum's row for its trace shape"
        )
    xs, ys = np.array(xs), np.array(ys)
    keep = np.ones(len(xs), bool)
    for _ in range(5):  # sigma-clipped polynomial
        coef = np.polyfit(xs[keep], ys[keep], min(order, keep.sum() - 1))
        resid = ys - np.polyval(coef, xs)
        new = np.abs(resid) < clip * max(np.std(resid[keep]), 1e-3)
        if np.array_equal(new, keep) or new.sum() < order + 2:
            break
        keep = new
    return coef


def shifted_trace(image, coef_ref, row, half_window=10):
    """The trace of a spectrum too faint to follow, with the shape of a brighter one (coef_ref) moved to it, as
    IRAF apall's reference aperture: `row` is the faint spectrum's row at the middle column; its exact offset is the
    peak of the frame summed along the reference shape (a supernova of a few counts per pixel next to a host star,
    real EFOSC2 night)."""
    from scipy.ndimage import map_coordinates

    ny, nx = image.shape
    x = np.arange(nx)
    y_ref = np.polyval(coef_ref, x)
    d0 = row - np.polyval(coef_ref, nx / 2)
    offsets = np.arange(d0 - half_window, d0 + half_window + 0.01, 0.25)
    profile = np.array(
        [np.nanmedian(map_coordinates(np.nan_to_num(image), [y_ref + d, x], order=1, mode="nearest")) for d in offsets]
    )
    profile -= np.median(profile)
    k = int(np.argmax(profile))
    w = np.clip(profile[max(0, k - 8) : k + 9], 0, None)
    d = offsets[max(0, k - 8) : k + 9]
    shift = float(np.sum(d * w) / np.sum(w)) if w.sum() > 0 else float(offsets[k])
    coef = np.array(coef_ref, float).copy()
    coef[-1] += shift
    return coef


def _band(image, coef, reach):
    """(first row, the rows a window `reach` around the trace can touch, the trace in them): masks over the whole
    frame for every order were most of an echelle reduction's time (46 orders x 8 Mpix on HARPS)."""
    ny, nx = image.shape
    yc = np.polyval(coef, np.arange(nx))
    lo = int(min(max(0, np.floor(np.nanmin(yc) - reach)), ny))
    hi = int(max(lo, min(ny, np.ceil(np.nanmax(yc) + reach) + 1)))
    c = np.array(coef, float).copy()
    c[-1] -= lo
    return lo, image[lo:hi], c


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
    import warnings

    _, image, coef = _band(image, coef, sky_offset + sky_width)
    _, sky = _windows(image.shape, coef, half_width, sky_offset, sky_width)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # columns where the trace leaves the frame: no sky (NaN)
        return np.nanmedian(np.where(sky, image, np.nan), axis=0)


def boxcar(image, coef, width=10.0, sky_offset=15.0, sky_width=10.0, subtract_sky=True):
    """Return (flux per column, sky per pixel per column). Arcs fill the slit: subtract_sky=False."""
    _, image, coef = _band(image, coef, max(width / 2, sky_offset + sky_width))
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
    shape = image.shape
    lo, image, coef = _band(image, coef, max(width / 2, sky_offset + sky_width))
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
    rejected = np.zeros(shape, bool)
    rejected[lo : lo + image.shape[0]] = obj & ~good
    return flux, err, sky, rejected
