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
from photutils.centroids import centroid_1dg, centroid_sources

_CLIP = SigmaClip(sigma=3.0, maxiters=10)


_last_fft = []  # [image, its transform] of the latest frame_shift call


def frame_shift(ref: np.ndarray, img: np.ndarray, binning: int = 1) -> tuple[float, float]:
    """(dx, dy) to add to positions in ref to find them in img: FFT phase correlation, sub-pixel peak.
    binning > 1 correlates binned frames: binning^2 times less work, about a tenth of a binned pixel of accuracy -
    enough where every star is re-centred afterwards (light curves), not for stacking.

    shortcut: translation only; rotated frames (alt-az, meridian flip) need plate solving or
    star-pattern matching before this."""

    from scipy import fft as sfft

    def prep(a):
        if binning > 1:
            ny, nx = (s // binning * binning for s in a.shape)
            a = np.asarray(a[:ny, :nx], np.float32).reshape(ny // binning, binning, nx // binning, binning).mean((1, 3))
        a = despike(a)  # hot pixels are fixed on the chip and would pull the peak to zero shift
        _, med, std = sigma_clipped_stats(a[::2, ::2])
        stars = np.clip(a - med - 3 * std, 0, 50 * std).astype(np.float64)  # no gradients, no saturated cores
        return sfft.rfft2(stars, workers=-1)  # real input: half the work of fft2, on every core; same correlation

    # frame to frame, this frame is the next call's reference: its transform is kept, not computed twice
    fa = _last_fft[1] if _last_fft and _last_fft[0] is ref and _last_fft[2] == binning else prep(ref)
    fb = prep(img)
    _last_fft[:] = [img, fb, binning]
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


def recenter(data, xy, box=11, max_move=2.5):
    """Centroids near the predicted (x, y) positions (0-based pixels). A centroid that fails or lands
    more than max_move pixels from the prediction (a neighbour, a defect) is replaced by the
    prediction. Centroids are found on a despiked copy so a hot pixel cannot capture them."""
    xy = np.asarray(xy, dtype=float)
    clean = np.nan_to_num(np.asarray(data, dtype=np.float32))
    ny, nx = clean.shape
    h = box // 2 + 2
    for px, py in xy:  # only around the stars: a whole-frame filter per frame dominated light curves
        if np.isfinite(px) and np.isfinite(py):
            y0, y1 = max(0, int(py) - h), min(ny, int(py) + h + 1)
            x0, x1 = max(0, int(px) - h), min(nx, int(px) + h + 1)
            if y1 - y0 >= 3 and x1 - x0 >= 3:
                clean[y0:y1, x0:x1] = despike(clean[y0:y1, x0:x1])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", AstropyUserWarning)  # a star wider than the box: handled below
        x, y = centroid_sources(clean, xy[:, 0], xy[:, 1], box_size=box, centroid_func=centroid_1dg)
    out = np.column_stack([x, y])
    sky = []  # the frame's sky level and noise, measured only if a star looks wider than the box

    def frame_sky():
        if not sky:
            _, med, std = sigma_clipped_stats(clean[::4, ::4])
            sky.extend([float(med), float(std)])
        return sky

    for i, (px, py) in enumerate(xy):  # defocused stars wider than the box: centre of light in a box that fits
        wide = _wide_centroid(clean, px, py, box, frame_sky) if np.isfinite(px) and np.isfinite(py) else None
        if wide is not None:
            out[i] = wide
    bad = ~np.isfinite(out).all(axis=1) | (np.hypot(*(out - xy).T) > max_move)
    out[bad] = xy[bad]
    return out


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
    edge = np.r_[small[0], small[-1], small[:, 0], small[:, -1]]
    if small.size == 0 or np.mean(edge) < 0.5 * np.max(small):  # light falling off inside the box: it fits
        return None
    sky, noise = frame_sky()
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


def measure(data, xy, r_ap, r_in, r_out, gain=1.0, pixel_noise=None):
    """Sky-subtracted flux, its error and sky level per pixel for each position (0-based x, y). pixel_noise: the
    sky noise per pixel when the file states it (TESS / Kepler pixel files); otherwise the scatter in the annulus."""
    data = np.asarray(data, dtype=np.float64)
    ap = CircularAperture(xy, r=r_ap)
    an = CircularAnnulus(xy, r_in=r_in, r_out=r_out)
    sky = ApertureStats(data, an, sigma_clip=_CLIP)
    raw = aperture_photometry(data, ap)
    n_ap = ap.area_overlap(data)
    n_sky = np.asarray(sky.sum_aper_area.value)
    flux = np.asarray(raw["aperture_sum"]) - n_ap * np.asarray(sky.median)
    noise = np.asarray(sky.std) if pixel_noise is None else float(pixel_noise)
    var = np.clip(flux, 0, None) / gain + n_ap * (1 + n_ap / n_sky) * noise**2
    return flux, np.sqrt(var), np.asarray(sky.median)


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


def choose_apertures(data, stars_xy, gain=1.0):
    """The three radii for the stars at stars_xy (target first, then the comparison stars), with the
    measurements behind them: FWHM, the S/N curve, the encircled energy and the profile to plot."""
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
