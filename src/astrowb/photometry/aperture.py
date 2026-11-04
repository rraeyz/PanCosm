"""Aperture photometry on a series of frames: frame offsets, re-centring, fluxes with errors.

Error per star (CCD equation in ADU, sky noise measured in the annulus, Merline & Howell 1995):
    var = F / gain + N_ap (1 + N_ap / N_sky) sigma_sky^2
where F is the sky-subtracted flux in the aperture, N_ap / N_sky the aperture / annulus pixel
counts and sigma_sky the sigma-clipped standard deviation of the annulus pixels.
"""

import warnings

import numpy as np
from astropy.stats import SigmaClip, sigma_clipped_stats
from astropy.utils.exceptions import AstropyUserWarning
from photutils.aperture import ApertureStats, CircularAnnulus, CircularAperture, aperture_photometry
from photutils.centroids import centroid_sources

_CLIP = SigmaClip(sigma=3.0, maxiters=10)


_last_fft = []  # [image, its transform, binning] of the latest frame_shift calls (the reference and the latest frame)


def bin_frame(a, binning):
    """Means of binning x binning pixels (the edge rows and columns that do not fill a bin are left out), float32.
    Strided sums: the same means as reshape(...).mean((1, 3)), five times faster (4k x 4k: 150 -> 30 ms)."""
    ny, nx = (s // binning * binning for s in a.shape)
    a = np.asarray(a[:ny, :nx], np.float32)
    return sum(a[i::binning, j::binning] for i in range(binning) for j in range(binning)) / np.float32(binning**2)


def frame_shift(ref: np.ndarray, img: np.ndarray, binning: int = 1) -> tuple[float, float]:
    """(dx, dy) to add to positions in ref to find them in img: FFT phase correlation, sub-pixel peak.
    binning > 1 correlates binned frames: binning^2 times less work, about a tenth of a binned pixel of accuracy -
    enough where every star is re-centred afterwards (light curves), not for stacking.

    shortcut: translation only; rotated frames (alt-az, meridian flip) need plate solving or
    star-pattern matching before this."""

    from scipy import fft as sfft

    def prep(a):
        if binning > 1:
            a = bin_frame(a, binning)
        a = despike(a)  # hot pixels are fixed on the chip and would pull the peak to zero shift
        _, med, std = sigma_clipped_stats(a[::2, ::2])
        stars = np.clip(a - med - 3 * std, 0, 50 * std).astype(np.float64)  # no gradients, no saturated cores
        return sfft.rfft2(stars, workers=-1)  # real input: half the work of fft2, on every core; same correlation

    # transforms are kept for the last two images: frame to frame (this frame is the next call's reference) and
    # every frame against one reference (light curves) each compute one transform per call, not two
    def cached(a):
        hit = next((e for e in _last_fft if e[0] is a and e[2] == binning), None)
        entry = hit or (a, prep(a), binning)
        _last_fft[:] = [*(e for e in _last_fft if e is not hit)][-1:] + [entry]  # the two latest used
        return entry[1]

    fa = cached(ref)
    fb = cached(img)
    shape = tuple(s // binning for s in img.shape)
    corr = sfft.irfft2(fb * np.conj(fa), s=shape, workers=-1)
    py, px = np.unravel_index(np.argmax(corr), corr.shape)

    def refine(c_m, c_0, c_p):
        d = c_m - 2 * c_0 + c_p
        return 0.0 if d == 0 else 0.5 * (c_m - c_p) / d

    ny, nx = corr.shape
    dy = py + refine(corr[(py - 1) % ny, px], corr[py, px], corr[(py + 1) % ny, px])
    dx = px + refine(corr[py, (px - 1) % nx], corr[py, px], corr[py, (px + 1) % nx])
    return binning * (dx - nx if dx > nx / 2 else dx), binning * (dy - ny if dy > ny / 2 else dy)


# Paeth's median-of-9 exchange network (19 min/max pairs): the 3x3 median of every pixel at once.
_MED9 = ((1, 2), (4, 5), (7, 8), (0, 1), (3, 4), (6, 7), (1, 2), (4, 5), (7, 8), (0, 3))
_MED9 += ((5, 8), (4, 7), (3, 6), (1, 4), (2, 5), (4, 7), (4, 2), (6, 4), (4, 2))


def despike(data, rows=512):
    """3x3 median filter: removes single hot/cold pixels and cosmic-ray hits, keeps stars (FWHM > 1.5 px).
    Same result as scipy.ndimage.median_filter(size=3, mode="reflect") on float32, about twice as fast (12 MP:
    2.1 s -> 1.0 s on two cores); done in blocks of rows so the memory stays small."""
    a = np.asarray(data, dtype=np.float32)
    bad = ~np.isfinite(a)
    if bad.any():  # pixels the flat could not correct: the sky level, not 0 (a hole would look like stars at its rim)
        a = np.where(bad, np.float32(np.nanmedian(a[::4, ::4])), a)
    ny, nx = a.shape
    padded = np.pad(a, 1, mode="symmetric")  # = scipy "reflect": the edge pixel is repeated
    out = np.empty_like(a)

    def block(y0):
        y1 = min(ny, y0 + rows)
        p = [padded[y0 + dy : y1 + dy, dx : dx + nx] for dy in range(3) for dx in range(3)]
        for i, j in _MED9:
            p[i], p[j] = np.minimum(p[i], p[j]), np.maximum(p[i], p[j])
        out[y0:y1] = p[4]

    starts = range(0, ny, rows)
    if len(starts) == 1:
        block(0)
    else:  # blocks of rows on every core (NumPy releases the GIL here); each block is the same computation
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor() as pool:
            list(pool.map(block, starts))
    return out


def centroid_1dg(data, mask=None, error=None):
    """photutils' centroid_1dg — 1-D Gaussians fitted to the marginal x and y sums, the same start values (moments)
    and the same least-squares settings (trf, analytic derivatives, xtol 1e-7, sigma > 0) — without astropy.modeling
    around it, which took 16 ms of the 17 per star (65 % of a TESS light curve). Same centres to 1e-6 px."""
    from scipy.optimize import least_squares

    data = np.array(data, dtype=float)
    weights = [np.ones(data.shape[1]), np.ones(data.shape[0])]
    if error is not None:
        e2 = np.asarray(error, float) ** 2
        weights = [1.0 / np.sqrt(np.sum(e2, axis=i)).clip(min=1.0e-30) for i in (0, 1)]
    bad = ~np.isfinite(data) | (np.zeros(data.shape, bool) if mask is None else np.asarray(mask, bool))
    if bad.any():
        data[bad] = 0.0
        for i in (0, 1):
            weights[i] = np.where(np.all(bad, axis=i), 0.0, weights[i])
    out = []
    for i in (0, 1):
        y, w = np.sum(data, axis=i), weights[i]
        if np.sum(y) == 0 or np.ptp(y) == 0:
            raise ValueError("Input data must have a nonzero sum and nonconstant values to fit 1D Gaussians.")
        x = np.arange(y.size, dtype=float)
        m = np.sum(x * y) / np.sum(y)
        p0 = [np.ptp(y), m, np.sqrt(abs(np.sum(y * (x - m) ** 2) / np.sum(y)))]

        def resid(p, x=x, y=y, w=w):
            return w * (p[0] * np.exp(-0.5 * (x - p[1]) ** 2 / p[2] ** 2) - y)

        def jac(p, x=x, w=w):
            g = np.exp(-0.5 * (x - p[1]) ** 2 / p[2] ** 2)
            return (
                np.column_stack([g, p[0] * g * (x - p[1]) / p[2] ** 2, p[0] * g * (x - p[1]) ** 2 / p[2] ** 3])
                * w[:, None]
            )

        tiny = float(np.finfo(np.float32).tiny)
        p0[2] = max(p0[2], tiny)
        fit = least_squares(resid, p0, jac=jac, method="trf", xtol=1e-7, max_nfev=100,
                            bounds=([-np.inf, -np.inf, tiny], [np.inf, np.inf, np.inf]))  # fmt: skip
        out.append(fit.x[1])
    return np.array(out)


def _unspike(stamp):
    """Only single hot/cold pixels and one-pixel cosmic-ray hits replaced by their 3x3 median: a pixel above its
    brightest neighbour by more than twice that neighbour's height over the median, or below all its neighbours.
    The core of an undersampled star (FWHM ~1.5 px, MicroObservatory HAT-P-32) has a neighbour nearly as bright and
    is kept: the full median filter halved it and moved the Gaussian centroid 2 px off the star."""
    from scipy.ndimage import maximum_filter, minimum_filter

    med = despike(stamp)
    ring = np.ones((3, 3), bool)
    ring[1, 1] = False
    hi = maximum_filter(stamp, footprint=ring, mode="nearest")
    lo = minimum_filter(stamp, footprint=ring, mode="nearest")
    return np.where((stamp - med > 2 * (hi - med)) | (stamp < lo), med, stamp)


def recenter(data, xy, box=11, max_move=2.5, found=False):
    """Centroids near the predicted (x, y) positions (0-based pixels). A centroid that fails or lands
    more than max_move pixels from the prediction (a neighbour, a defect) is replaced by the
    prediction. Centroids are found on a copy without single hot pixels so one cannot capture them.
    found: also return which positions are centroids (True) rather than the prediction kept (False)."""
    xy = np.asarray(xy, dtype=float)
    clean = np.nan_to_num(np.asarray(data, dtype=np.float32))
    ny, nx = clean.shape
    h = box // 2 + 2
    for px, py in xy:  # only around the stars: a whole-frame filter per frame dominated light curves
        if np.isfinite(px) and np.isfinite(py):
            y0, y1 = max(0, int(py) - h), min(ny, int(py) + h + 1)
            x0, x1 = max(0, int(px) - h), min(nx, int(px) + h + 1)
            if y1 - y0 >= 3 and x1 - x0 >= 3:
                clean[y0:y1, x0:x1] = _unspike(clean[y0:y1, x0:x1])
    out = np.full_like(xy, np.nan)
    inside = np.isfinite(xy).all(axis=1) & (xy[:, 0] >= 0) & (xy[:, 0] <= nx - 1) & (xy[:, 1] >= 0)
    inside &= xy[:, 1] <= ny - 1  # a position off the frame (a wrong shift, a cloud): not found, never an error
    if inside.any():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", AstropyUserWarning)  # a star wider than the box: handled below
            x, y = centroid_sources(clean, xy[inside, 0], xy[inside, 1], box_size=box, centroid_func=centroid_1dg)
        out[inside] = np.column_stack([x, y])
    sky = []  # the frame's sky level and noise, measured only if a star looks wider than the box

    def frame_sky():
        if not sky:
            _, med, std = sigma_clipped_stats(clean[::4, ::4])
            sky.extend([float(med), float(std)])
        return sky

    for i, (px, py) in enumerate(xy):  # defocused stars wider than the box: centre of light in a box that fits
        wide = _wide_centroid(clean, px, py, box, frame_sky) if inside[i] else None
        if wide is not None:
            out[i] = wide
    bad = ~np.isfinite(out).all(axis=1) | (np.hypot(*(out - xy).T) > max_move)
    out[bad] = xy[bad]
    return (out, ~bad) if found else out


def _wide_centroid(img, x, y, box, frame_sky, max_box=301):
    """Centre of a star wider than the centroid box (defocused; or a donut, whose centre is dark): the extent of
    the star from its azimuthally averaged profile around (x, y) (a neighbour fills only a little of each ring, so
    it does not count), then the sky-subtracted centre of light in a box that holds the star, iterated.
    None for a star that fits the box: its Gaussian centroid is kept, unchanged. The Gaussian centroid in an
    11-pixel box was off by 1.8 px for FWHM 40-60 px stars (tests/test_apertures.py)."""
    ny, nx = img.shape
    h0 = box // 2
    y0, x0 = int(round(y)), int(round(x))
    small = img[max(0, y0 - h0) : y0 + h0 + 1, max(0, x0 - h0) : x0 + h0 + 1]
    if small.size == 0:
        return None
    sky, noise = frame_sky()
    hole = np.max(small) - sky < 5 * noise  # nothing in the box: the dark centre of a donut wider than the box
    edge = np.r_[small[0], small[-1], small[:, 0], small[:, -1]]
    rising = np.max(edge) >= np.max(small)  # brightest on the box's edge: a donut's ring seen from inside the hole
    if not (hole or rising) and np.mean(edge) < 0.5 * np.max(small):  # light falling off inside the box: it fits
        return None
    h = min(max_box // 2, y0, x0, ny - 1 - y0, nx - 1 - x0)
    if h <= h0:
        return None
    win = img[y0 - h : y0 + h + 1, x0 - h : x0 + h + 1].astype(float) - sky
    yy, xx = np.indices(win.shape)
    r = np.hypot(xx - (x - x0 + h), yy - (y - y0 + h)).astype(int)
    keep = r <= h
    n = np.bincount(r[keep], minlength=h + 1)
    prof = np.bincount(r[keep], weights=win[keep], minlength=h + 1) / np.maximum(n, 1)
    peak = int(np.argmax(prof))
    if prof[peak] < 5 * noise / np.sqrt(max(n[peak], 1)) or (peak <= h0 and prof[h0] < 0.2 * prof[peak]):
        return None  # no significant light, or a star that fits the box
    faded = np.flatnonzero((np.arange(h + 1) > peak) & (prof < 0.02 * prof[peak]))
    if not len(faded):
        return None  # the star does not fade out inside max_box
    b = 2 * int(np.ceil(1.3 * faded[0])) + 1
    for _ in range(10):
        hb = b // 2
        cy0, cx0 = int(round(y)) - hb, int(round(x)) - hb
        if cy0 < 0 or cx0 < 0 or cy0 + b > ny or cx0 + b > nx:
            return None
        c = img[cy0 : cy0 + b, cx0 : cx0 + b].astype(float) - sky
        w = np.where(c > 3 * noise, c, 0.0)
        if w.sum() <= 0:
            return None
        iy, ix = np.indices(w.shape)
        cx, cy = cx0 + (w * ix).sum() / w.sum(), cy0 + (w * iy).sum() / w.sum()
        done = np.hypot(cx - x, cy - y) < 0.005
        x, y = cx, cy
        if done:
            break
    return x, y


def _grouped_median(values):
    """Median of integer-valued samples (raw ADU of 8 to 16-bit cameras) without the rounding to a whole number: the
    median taken inside its unit bin as for grouped data (median = L + (n/2 - below) / in_bin). The plain median of
    integers is off by up to 0.5 ADU, which over a 50-pixel aperture moved faint stars by up to 1 % against IRAF
    phot (HAT-P-32 sample night, plans/photometry.md item 1). Non-integer data keep the plain median."""
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.nan
    med = float(np.median(v))
    if med != round(med) or not np.all(v == np.round(v)):
        return med
    below, inside = np.count_nonzero(v < med - 0.5), np.count_nonzero(v == med)
    return med - 0.5 + (v.size / 2 - below) / inside


def star_mask(shape, xy, radius):
    """True within radius of each (x, y): the stars to leave out of the sky rings (measure's sky_mask)."""
    out = np.zeros(shape, bool)
    for x, y in np.asarray(xy, float).reshape(-1, 2):
        y0, y1 = max(int(y - radius), 0), min(int(y + radius) + 2, shape[0])
        x0, x1 = max(int(x - radius), 0), min(int(x + radius) + 2, shape[1])
        yy, xx = np.mgrid[y0:y1, x0:x1]
        out[y0:y1, x0:x1] |= (xx - x) ** 2 + (yy - y) ** 2 <= radius * radius
    return out


def _sky_medians(data, an, sky):
    """sky.median, corrected for integer-valued data (_grouped_median) on the same clipped ring pixels."""
    med = np.atleast_1d(np.asarray(sky.median, float)).copy()
    for i, mask in enumerate(an.to_mask(method="center") if np.ndim(an.positions) > 1 else [an.to_mask("center")]):
        vals = mask.get_values(data)
        if vals.size and np.all(vals == np.round(vals)):
            med[i] = _grouped_median(_CLIP(vals, masked=True).compressed())
    return med if np.ndim(sky.median) else med[0]


QUANTISATION = 0.289  # rms of the rounding to whole ADU, 1/sqrt(12) (Merline & Howell 1995; AstroImageJ)


def camera_pixel_noise(sky, gain, read_noise, dark):
    """Noise of one sky pixel (ADU) from the camera: sky photons, dark current and read noise in electrons, and the
    rounding to whole ADU — sqrt(S g + D + R^2 + 0.289^2 g^2) / g, AstroImageJ's model (Collins et al. 2017, appendix
    B; Merline & Howell 1995). sky: ADU per pixel above the bias; dark: electrons per pixel over the exposure."""
    sky = np.clip(np.asarray(sky, float), 0, None)
    return np.sqrt(sky * gain + dark + read_noise**2 + (QUANTISATION * gain) ** 2) / gain


SKY_METHODS = ("median", "mode", "mean", "plane", "centroid")


def sky_estimate(values, dx, dy, method="median"):
    """Sky level at the star's centre and the scatter of one pixel, from the ring's pixel values and their offsets
    (dx, dy) from the centre, with the number of pixels kept (plans/photometry.md item 3):
    - "median": 3-sigma clipped median (inside its bin for integer data, _grouped_median);
    - "mode": IRAF's 3 median - 2 mean after iterative 3-sigma clipping (fitskypars salgorithm=mode);
    - "mean": AstroImageJ's: pixels within mean +- 2 sigma, iterated until the mean changes by < 1e-4 (100 at most);
    - "plane": a plane a + b dx + c dy fitted to the ring with 3-sigma clipping of the residuals (gradients from the
      Moon or twilight); its value at the centre is the sky, and over a whole circular aperture the tilt cancels;
    - "centroid": IRAF's (fitskypars salgorithm=centroid): the centroid of the ring's histogram within ± 3 sigma of
      the median in bins of 0.1 sigma, pixels beyond 3 sigma of it rejected and the histogram made again (10 times
      at most)."""
    v, dx, dy = (np.asarray(a, float) for a in (values, dx, dy))
    ok = np.isfinite(v)
    v, dx, dy = v[ok], dx[ok], dy[ok]
    if v.size < 3:
        return np.nan, np.nan, int(v.size)
    if method == "plane":
        keep = np.ones(v.size, bool)
        for _ in range(10):
            A = np.column_stack([np.ones(keep.sum()), dx[keep], dy[keep]])
            coef, *_ = np.linalg.lstsq(A, v[keep], rcond=None)
            resid = v - (coef[0] + coef[1] * dx + coef[2] * dy)
            sd = 1.4826 * np.median(np.abs(resid[keep] - np.median(resid[keep])))
            new = np.abs(resid) <= 3 * max(sd, 1e-12)
            if (new == keep).all():
                break
            keep = new
        return float(coef[0]), float(np.std(resid[keep])), int(keep.sum())
    if method == "mean":
        keep = np.ones(v.size, bool)
        mean = v.mean()
        for _ in range(100):
            sd = v[keep].std()
            new = np.abs(v - mean) <= 2 * sd
            m2 = v[new].mean() if new.any() else mean
            keep = new
            if abs(m2 - mean) < 1e-4 * max(abs(mean), 1.0):
                mean = m2
                break
            mean = m2
        return float(mean), float(v[keep].std()), int(keep.sum())
    if method == "centroid":
        return _histogram_centroid(v)
    kept = _CLIP(v, masked=True).compressed()
    if method == "mode":
        return float(3 * np.median(kept) - 2 * kept.mean()), float(kept.std()), int(kept.size)
    return float(_grouped_median(kept)), float(kept.std()), int(kept.size)


def _histogram_centroid(v, khist=3.0, binsize=0.1, reject=3.0, maxiter=10):
    keep = np.ones(v.size, bool)
    centre, sd = float(np.median(v)), float(v.std())
    for _ in range(maxiter):
        if sd <= 0:
            return centre, 0.0, int(keep.sum())
        edges = np.arange(centre - khist * sd, centre + khist * sd + binsize * sd / 2, binsize * sd)
        counts, edges = np.histogram(v[keep], edges)
        if counts.sum() == 0:
            break
        centre = float(np.sum(counts * (edges[:-1] + edges[1:]) / 2) / counts.sum())
        new = keep & (np.abs(v - centre) <= reject * sd)
        sd = float(v[new].std())
        if (new == keep).all():
            break
        keep = new
    return centre, sd, int(keep.sum())


def measure(data, xy, r_ap, r_in, r_out, gain=1.0, pixel_noise=None, camera=None, sky_method="median", sky_mask=None):
    """Sky-subtracted flux, its error and sky level per pixel for each position (0-based x, y). pixel_noise: the
    sky noise per pixel when the file states it (TESS / Kepler pixel files); otherwise the scatter in the annulus.
    camera (read noise e-, dark e- per pixel over the exposure): the sky noise from the camera's numbers and each
    star's sky level instead (camera_pixel_noise), as AstroImageJ does (plans/photometry.md item 2).
    sky_mask: pixels (True) left out of every sky ring — other stars, whose faint wings clipping keeps (PHO-45)."""
    data = np.asarray(data, dtype=np.float64)
    ap = CircularAperture(xy, r=r_ap)
    an = CircularAnnulus(xy, r_in=r_in, r_out=r_out)
    ring = data if sky_mask is None else np.where(sky_mask, np.nan, data)
    sky = ApertureStats(data, an, sigma_clip=_CLIP, mask=sky_mask)
    raw = aperture_photometry(data, ap)
    n_ap = ap.area_overlap(data)
    n_sky = np.asarray(sky.sum_aper_area.value)
    median = _sky_medians(ring, an, sky)
    std = np.asarray(sky.std, float)
    if sky_method != "median":  # the other estimators work on the ring's pixels and their places
        median, std, n_sky = (np.atleast_1d(np.array(a, float)).copy() for a in (median, std, n_sky))
        for i, (x, y) in enumerate(np.atleast_2d(np.asarray(xy, float))):
            mask = CircularAnnulus((x, y), r_in=r_in, r_out=r_out).to_mask(method="center")
            vals = mask.get_values(ring)
            yy, xx = np.mgrid[mask.bbox.iymin : mask.bbox.iymax, mask.bbox.ixmin : mask.bbox.ixmax]
            inside = mask.data > 0
            cut = mask.get_overlap_slices(data.shape)[1]
            if cut is None:
                continue
            xs, ys = xx[cut][inside[cut]], yy[cut][inside[cut]]
            median[i], std[i], n_sky[i] = sky_estimate(vals, xs - x, ys - y, sky_method)
    flux = np.asarray(raw["aperture_sum"]) - n_ap * median
    if camera is not None:
        noise = camera_pixel_noise(median, gain, *camera)
    else:
        noise = std if pixel_noise is None else float(pixel_noise)
    var = np.clip(flux, 0, None) / gain + n_ap * (1 + n_ap / n_sky) * noise**2
    return flux, np.sqrt(var), median


def measure_cube(cube, xy, r_ap, r_in, r_out, gain=1.0, pixel_noise=None):
    """measure() on every frame of a cube (n, ny, nx) with the stars at fixed positions, all frames at once: the same
    apertures (exact overlap), sky rings (pixel centres, 3-sigma clipped median and scatter) and errors; and the
    brightest pixel in each aperture. pixel_noise: per frame (n), or None. Returns flux, err, sky (n, stars), peak."""
    from astropy.stats import sigma_clip

    cube = np.asarray(cube, np.float32)
    n, shape = len(cube), cube.shape[1:]
    flux, err, sky, peak = (np.full((n, len(xy)), np.nan) for _ in range(4))
    for k, (x, y) in enumerate(np.asarray(xy, float)):
        ap, an = CircularAperture((x, y), r=r_ap), CircularAnnulus((x, y), r_in=r_in, r_out=r_out)
        m = ap.to_mask(method="exact")
        big, small = m.get_overlap_slices(shape)
        if big is None:
            continue
        part = cube[(slice(None), *big)]
        total = np.einsum("nij,ij->n", part.astype(np.float64), m.data[small])
        centre = ap.to_mask(method="center").data[small] > 0
        peak[:, k] = part[:, centre].max(axis=1) if centre.any() else np.nan
        mr = an.to_mask(method="center")
        big_r, small_r = mr.get_overlap_slices(shape)
        ring = cube[(slice(None), *big_r)][:, mr.data[small_r] > 0].astype(np.float64)
        clipped = sigma_clip(ring, sigma=3.0, maxiters=10, axis=1)
        med = np.ma.median(clipped, axis=1).filled(np.nan)
        std = np.ma.std(clipped, axis=1).filled(np.nan)
        n_ap = ap.area_overlap(cube[0])
        me = an.to_mask(method="exact")  # the ring's area without the clipped pixels, as ApertureStats counts it
        big_e, small_e = me.get_overlap_slices(shape)
        we = me.data[small_e]
        vals = cube[(slice(None), *big_e)][:, we > 0].astype(np.float64)
        keep = ~np.ma.getmaskarray(sigma_clip(vals, sigma=3.0, maxiters=10, axis=1))  # clipped on these pixels
        n_sky = keep @ we[we > 0]
        flux[:, k] = total - n_ap * med
        noise = std if pixel_noise is None else np.asarray(pixel_noise, float)
        err[:, k] = np.sqrt(np.clip(flux[:, k], 0, None) / gain + n_ap * (1 + n_ap / n_sky) * noise**2)
        sky[:, k] = med
    return flux, err, sky, peak


def suggest_comparisons(data, target_xy, r_out, n=5, saturation=None, r_in=None, offsets=((0.0, 0.0),)):
    """Up to n comparison stars (0-based x, y): similar brightness (0.5-2x the target), not saturated,
    no neighbour inside the sky annulus, and inside the frame (with the annulus) in every frame of the
    series, given the frame offsets relative to this one. Best match first: similar brightness and near the
    target (as AstroImageJ users are advised: the star image changes across a wide field, and comparisons at the
    frame's edge followed the seeing unlike the target on a real LCO night, shifting a transit by 20 min)."""
    from photutils.detection import DAOStarFinder

    clean = despike(data)
    _, med, std = sigma_clipped_stats(clean[::2, ::2])
    raw_std = sigma_clipped_stats(np.asarray(data, float)[::2, ::2])[2]
    stars = DAOStarFinder(fwhm=3.0, threshold=5 * std)(clean - med)
    if stars is None:
        return []
    x, y = np.asarray(stars["x_centroid"]), np.asarray(stars["y_centroid"])
    flux, peak = np.asarray(stars["flux"]), np.asarray(stars["peak"]) + med
    t = np.argmin(np.hypot(x - target_xy[0], y - target_xy[1]))
    saturation = saturation or 0.9 * float(np.nanmax(data))
    ny, nx = data.shape
    off = np.asarray(offsets, float)
    margin = r_out + 2
    r_in = r_in or r_out / 2
    yy, xx = np.mgrid[:ny, :nx]
    picks = []
    score = np.abs(np.log(np.clip(flux / flux[t], 1e-12, None))) + np.hypot(x - x[t], y - y[t]) / np.hypot(nx, ny) * 2
    for i in np.argsort(score):  # similar brightness and close to the target first
        px, py = x[i] + off[:, 0], y[i] + off[:, 1]
        inside = np.all((px >= margin) & (px < nx - margin) & (py >= margin) & (py < ny - margin))
        if not inside:
            continue
        # isolated: no neighbour in the sky annulus brighter than 20 % of the star's peak (fainter ones are
        # removed by the sigma-clipped sky). Tested on pixels, not on the star list: blends hide.
        r = np.hypot(xx - x[i], yy - y[i])
        isolated = np.max(clean[(r > r_in) & (r < r_out)]) - med < max(0.2 * (peak[i] - med), 5 * raw_std)
        if i != t and 0.5 <= flux[i] / flux[t] <= 2 and peak[i] < saturation and isolated and inside:
            picks.append((float(x[i]), float(y[i])))
        if len(picks) == n:
            break
    return picks


# --- choosing the three radii from the stars themselves --------------------------------------------------------
# Ring 1, the aperture: the radius where the differential measurement has the best signal-to-noise, found on the
#   curve of growth with the CCD equation above (Howell 1989, PASP 101, 616), kept between 1 and 3 FWHM (smaller
#   apertures lose a seeing-dependent part of the light and suffer from centring errors).
# Gap between rings 1 and 2: left out; it holds the star's wings, which would bias the sky upwards.
# Ring 2, inner sky radius: where the brightest selected star has given 99.5 % of its light (encircled energy),
#   and at least 3 FWHM: real seeing profiles have wings (Moffat, scattered light) and the seeing changes during
#   the night, so the usual practice (e.g. the defaults of AstroImageJ and IRAF users) keeps the sky that far out.
# Ring 3, outer sky radius: the annulus holds SKY_RATIO times as many pixels as the aperture, so the sky term
#   (1 + N_ap / N_sky) adds only 25 % to the sky noise (Merline & Howell 1995, ExA 6, 163).
SKY_RATIO = 4.0
ENCIRCLED = 0.995


def _moffat(r, a, alpha, beta):
    return a * (1 + (r / alpha) ** 2) ** -beta


def star_profile(data, x, y, r_max):
    """Radial profile of one star: pixel radii and sky-subtracted values within r_max, the sky level and its
    scatter (sigma-clipped, from the outer 30 % of r_max) and the FWHM of a Moffat fit (half-maximum crossing of
    the binned profile when the fit fails, e.g. a defocused ring)."""
    from scipy.optimize import curve_fit

    ny, nx = data.shape
    x0, x1 = max(0, int(x - r_max)), min(nx, int(x + r_max) + 2)
    y0, y1 = max(0, int(y - r_max)), min(ny, int(y + r_max) + 2)
    yy, xx = np.mgrid[y0:y1, x0:x1]
    r = np.hypot(xx - x, yy - y).ravel()
    v = np.asarray(data[y0:y1, x0:x1], float).ravel()
    keep = (r <= r_max) & np.isfinite(v)
    r, v = r[keep], v[keep]
    _, sky, sky_std = sigma_clipped_stats(v[r > 0.7 * r_max])
    v = v - sky
    edges = np.arange(0, r_max + 0.5, 0.5)
    idx = np.digitize(r, edges) - 1
    binned = np.array([np.mean(v[idx == i]) if np.any(idx == i) else np.nan for i in range(len(edges) - 1)])
    centres = edges[:-1] + 0.25
    peak = np.nanmax(binned[:4])
    below = np.nonzero(binned < peak / 2)[0]
    half = centres[below[0]] if len(below) else r_max / 2
    fwhm = 2 * half
    inner = r < 0.5 * r_max
    try:
        p, _ = curve_fit(
            _moffat, r[inner], v[inner], p0=(peak, max(half, 0.5), 2.5), bounds=((0, 0.2, 1.0), (np.inf, r_max, 20))
        )
        moffat = 2 * p[1] * np.sqrt(2 ** (1 / p[2]) - 1)
        if 0.3 * fwhm < moffat < 3 * fwhm:  # a failed fit lands far from the half-maximum estimate
            fwhm = float(moffat)
    except (RuntimeError, ValueError):
        pass
    out = {"r": r, "v": v, "sky": float(sky), "sky_std": float(sky_std), "fwhm": float(fwhm)}
    return out | {"bins": (centres, binned)}


def seeing_fwhm(data, xy, r_max=25.0):
    """Median FWHM (pixels) of the stars at xy on one frame."""
    data = np.asarray(data, float)
    return float(np.median([star_profile(data, x, y, r_max)["fwhm"] for x, y in xy]))


def choose_apertures(data, stars_xy, gain=1.0, rule="snr"):
    """The three radii for the stars at stars_xy (target first, then the comparison stars), with the
    measurements behind them: FWHM, the S/N curve, the encircled energy and the profile to plot.
    rule "aij": AstroImageJ's automatic radii instead (aij_radii), so that both programs can measure a night with the
    same apertures (plans/photometry.md item 1)."""
    data = np.asarray(data, float)
    xy = recenter(data, stars_xy, max_move=5.5)  # clicked positions: snapped onto the stars within half the box
    # a small stamp (a TESS / Kepler pixel file, 13 x 11 px) has no pixels 25 px away: profiles end in its corners
    ny, nx = data.shape
    corner = 0.95 * min(np.hypot(max(x, nx - 1 - x), max(y, ny - 1 - y)) for x, y in xy)
    fwhm = seeing_fwhm(data, xy, min(25.0, corner))
    r_max = min(max(25.0, 8 * fwhm), corner)  # sky for the profile far beyond the wings
    profiles = [star_profile(data, x, y, r_max) for x, y in xy]
    fwhm = float(np.median([p["fwhm"] for p in profiles]))
    radii = np.arange(0.5, 0.6 * r_max, 0.25)
    growth, area = [], []
    for p in profiles:  # enclosed flux (sky-subtracted) and pixel count at every radius, pixel-centre sampling
        order = np.argsort(p["r"])
        n = np.searchsorted(p["r"][order], radii, side="right")
        growth.append(np.concatenate([[0.0], np.cumsum(p["v"][order])])[n])
        area.append(n)
    growth, area = np.array(growth), np.array(area, float)
    sky_var = np.array([p["sky_std"] ** 2 for p in profiles])[:, None]
    var = np.clip(growth, 0, None) / gain + area * (1 + 1 / SKY_RATIO) * sky_var
    with np.errstate(divide="ignore", invalid="ignore"):
        rel2 = var[0] / growth[0] ** 2  # relative variance of the target
        if len(profiles) > 1:  # of target / sum(comparisons), as in the light curve
            rel2 = rel2 + var[1:].sum(axis=0) / growth[1:].sum(axis=0) ** 2
        snr = 1 / np.sqrt(rel2)
    snr = np.where(np.isfinite(snr) & (growth[0] > 0), snr, 0.0)
    best = float(radii[np.argmax(snr)])
    r_ap = float(np.clip(best, 1.0 * fwhm, 3.0 * fwhm))
    plateau = (radii >= 0.45 * r_max) & (radii <= 0.6 * r_max)
    total = np.median(growth[:, plateau], axis=1)
    b = int(np.argmax(total))  # the brightest star has the best measured wings
    ee = growth[b] / total[b]
    enough = np.nonzero((ee >= ENCIRCLED) & (radii > r_ap))[0]
    r_in = float(radii[enough[0]]) if len(enough) else 3.0 * fwhm
    r_in = max(r_in, 3.0 * fwhm, r_ap + 1.0)
    r_out = float(np.sqrt(r_in**2 + SKY_RATIO * r_ap**2))
    if r_out > r_max:  # a small stamp: a narrow ring from 2 FWHM, not out in its corners (on a real 11 x 11 px TESS
        # file of WASP-12 the corners held a neighbour and few pixels: scatter 0.0036 against 0.0026 for 4-6 px)
        r_in = max(min(r_in, 2.0 * fwhm, r_max - 1.0), r_ap + 0.5)
        r_out = max(min(r_max, r_in + 2.0), r_in + 1.0)
    centres, binned = profiles[b]["bins"]
    if rule == "aij":
        r_ap, r_in, r_out = aij_radii(*profiles[0]["bins"], fwhm)
    # a target whose light grows faster outside the aperture than the comparisons' has something next to it (a faint
    # neighbour in its wings): radii that follow the seeing then take a varying share of it (tested on a synthetic
    # blend; on stars without one the value stays within +-0.4 %)
    with np.errstate(divide="ignore", invalid="ignore"):
        g = np.interp(1.5 * r_ap, radii, growth[0]) / np.interp(r_ap, radii, growth[0])
        others = [np.interp(1.5 * r_ap, radii, gr) / np.interp(r_ap, radii, gr) for gr in growth[1:]]
    excess = float(g - np.median(others)) if others else 0.0
    return {
        "target_excess": excess if np.isfinite(excess) else 0.0,
        "fwhm": fwhm,
        "r_ap": round(r_ap, 2),
        "r_in": round(r_in, 2),
        "r_out": round(r_out, 2),
        "best_snr_radius": best,
        "snr_at_aperture": float(np.interp(r_ap, radii, snr)),
        "encircled_at_aperture": float(np.interp(r_ap, radii, ee)),
        "profile_r": centres.tolist(),
        "profile": (binned / np.nanmax(binned[:4])).tolist(),
        "radii": radii.tolist(),
        "snr": snr.tolist(),
        "encircled": ee.tolist(),
    }


AIJ_CUTOFF = 0.010  # AstroImageJ's autoModeFluxCutOff: the aperture ends where the profile falls to 1 % of its peak


def aij_radii(centres, binned, fwhm, cutoff=AIJ_CUTOFF):
    """AstroImageJ's automatic radii (its Seeing_Profile, read 2026-11-08; the rule, not the code): the aperture ends
    at the first radius beyond the half maximum where the star's mean profile falls below 1 % of its peak, the sky
    ring runs from twice to four times that, each rounded up to a whole pixel; when the profile never falls that low
    (a wide or noisy star), 1.7, 3.4 and 6.8 FWHM cut to whole pixels."""
    centres, binned = np.asarray(centres, float), np.asarray(binned, float)
    norm = binned / np.nanmax(binned[:4])
    past_half = np.nonzero(norm <= 0.5)[0]
    if len(past_half):
        low = np.nonzero(
            (norm < cutoff) & (np.arange(norm.size) > past_half[0]) & (np.arange(norm.size) < norm.size - 5)
        )[0]
        if len(low):
            r1 = float(np.ceil(centres[low[0]]))
            return r1, 2 * r1, 4 * r1
    return float(int(1.7 * fwhm)), float(int(3.4 * fwhm)), float(int(6.8 * fwhm))


# Scintillation: the twinkling of a star in the atmosphere adds a relative noise that photon statistics miss
# (dominant for bright stars and short exposures). Osborn et al. 2015 (MNRAS 452, 1707), eq. 7, the corrected
# form of Young (1967): sigma^2 = 10e-6 C_Y^2 D^(-4/3) t^(-1) X^3 exp(-2 h / H), with D the telescope aperture
# (m), t the exposure (s), X the airmass, h the observatory height (m), H = 8000 m and C_Y = 1.5, the median of
# the empirical coefficient over the sites they studied.
SCINT_C_Y = 1.5
SCINT_H = 8000.0


def scintillation(diameter_m, exptime_s, airmass, height_m=0.0, c_y=SCINT_C_Y):
    """Relative scintillation noise (sigma of flux / flux) of one exposure."""
    d, t, x = float(diameter_m), float(exptime_s), np.asarray(airmass, float)
    if not (d > 0 and t > 0):
        raise ValueError("the telescope aperture and the exposure time must be positive")
    return np.sqrt(10e-6 * c_y**2 * d ** (-4 / 3) / t * x**3 * np.exp(-2 * float(height_m) / SCINT_H))
