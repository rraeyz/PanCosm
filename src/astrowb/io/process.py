"""General image operations. Each returns (new image, new header); geometric operations carry the
celestial WCS along (an exact pixel-affine transform of CD/PC and CRPIX), so a plate-solved image
stays solved.

Images are numpy [y, x] with FITS orientation (row 0 at the bottom).
"""

import re

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from ..hdr import number


def _with_wcs(header, m, t):
    """Header whose celestial WCS follows a pixel mapping old = M @ new + t (0-based (x, y) pixels):
    CD' = CD M, CRPIX' = M^-1 (CRPIX - 1 - t) + 1. SIP distortion survives pure shifts (crops) only."""
    h = header.copy()
    try:
        w = WCS(header)
    except Exception:  # a WCS that cannot be read cannot be moved: dropped, never left pointing at the wrong sky
        stale = [k for k in h if re.match(r"(CTYPE|CRPIX|CRVAL|CDELT|CUNIT|CROTA|CD\d_|PC\d_|[AB]P?_)", k)]
        for k in stale:
            h.remove(k, ignore_missing=True, remove_all=True)
        if stale:
            h.add_history("unreadable WCS removed by a geometric operation; plate-solve again")
        return h
    if not w.has_celestial:
        return h
    m, t = np.asarray(m, float), np.asarray(t, float)
    c = w.celestial.deepcopy()
    shift_only = np.allclose(m, np.eye(2))
    if c.wcs.has_cd():
        c.wcs.cd = c.wcs.cd @ m
    else:
        c.wcs.pc = c.wcs.get_pc() @ m
    c.wcs.crpix = np.linalg.solve(m, c.wcs.crpix - 1 - t) + 1
    if c.sip is not None and not shift_only:
        c.sip = None
        h.add_history("distortion (SIP) terms dropped by a geometric operation")
    for key in list(w.celestial.to_header(relax=True)):
        h.remove(key, ignore_missing=True, remove_all=True)
    for k in ("CD1_1", "CD1_2", "CD2_1", "CD2_2", "PC1_1", "PC1_2", "PC2_1", "PC2_2"):
        h.remove(k, ignore_missing=True, remove_all=True)
    for k in [k for k in h if k.startswith(("A_", "B_", "AP_", "BP_"))]:
        h.remove(k, ignore_missing=True, remove_all=True)
    h.update(c.to_header(relax=True))
    return h


def flip(data, header, axis):
    """axis "x": mirror left-right; "y": mirror top-bottom."""
    ny, nx = data.shape
    if axis == "x":
        return data[:, ::-1], _with_wcs(header, [[-1, 0], [0, 1]], [nx - 1, 0])
    return data[::-1, :], _with_wcs(header, [[1, 0], [0, -1]], [0, ny - 1])


def rotate90(data, header, k=1):
    """Rotate by k x 90 degrees (as displayed, FITS orientation)."""
    out, h = data, header
    for _ in range(int(k) % 4):  # out[y', x'] = old[ny - 1 - x', y']
        ny = out.shape[0]
        out, h = out.T[:, ::-1], _with_wcs(h, [[0, 1], [-1, 0]], [0, ny - 1])
    return out, h


def crop(data, header, x0, x1, y0, y1):
    """Keep columns x0..x1-1 and rows y0..y1-1 (0-based, clipped to the image)."""
    ny, nx = data.shape
    x0, x1 = max(0, int(x0)), min(nx, int(x1))
    y0, y1 = max(0, int(y0)), min(ny, int(y1))
    if x1 <= x0 or y1 <= y0:
        raise ValueError("empty crop region")
    return data[y0:y1, x0:x1], _with_wcs(header, np.eye(2), [x0, y0])


def _resample(data, m, t, shape):
    """New image of the given shape whose pixel (x, y) takes the old image at M @ (x, y) + t (bilinear; outside
    the old image: NaN)."""
    from scipy.ndimage import map_coordinates

    yy, xx = np.mgrid[: shape[0], : shape[1]].astype(float)
    xs = m[0, 0] * xx + m[0, 1] * yy + t[0]
    ys = m[1, 0] * xx + m[1, 1] * yy + t[1]
    out = map_coordinates(np.asarray(data, float), [ys, xs], order=1, cval=np.nan, prefilter=False)
    return out.astype(np.float32)


def rotate(data, header, angle=0.0):
    """Turn the image counter-clockwise (as displayed) by angle degrees about its centre. The size is kept;
    corners that come from outside the old image are blank (NaN). Bilinear, so a star keeps its counts."""
    ny, nx = data.shape
    a = np.radians(float(angle))
    m = np.array([[np.cos(a), np.sin(a)], [-np.sin(a), np.cos(a)]])  # old = R(-angle) (new - c) + c
    c = np.array([(nx - 1) / 2, (ny - 1) / 2])
    t = c - m @ c
    return _resample(data, m, t, data.shape), _with_wcs(header, m, t)


def resample(data, header, factor=2.0):
    """A pixel grid `factor` times finer (> 1) or coarser (< 1). Values are divided by factor^2, so the counts of a
    star (and the total) stay the same."""
    f = float(factor)
    if not f > 0:
        raise ValueError("the factor must be positive")
    shape = tuple(max(1, round(n * f)) for n in data.shape)
    m, t = np.eye(2) / f, np.full(2, (1 / f - 1) / 2)  # pixel centres: old = (new + 0.5) / f - 0.5
    return _resample(data, m, t, shape) / np.float32(f * f), _with_wcs(header, m, t)


def bin_image(data, header, factor=2, mode="mean"):
    """Combine factor x factor pixels (edges that do not fill a block are dropped)."""
    f = int(factor)
    ny, nx = (s // f * f for s in data.shape)
    blocks = data[:ny, :nx].reshape(ny // f, f, nx // f, f)
    out = np.nansum(blocks, axis=(1, 3)) if mode == "sum" else np.nanmean(blocks, axis=(1, 3))
    h = _with_wcs(header, f * np.eye(2), [(f - 1) / 2, (f - 1) / 2])
    for key in ("XBINNING", "YBINNING"):
        if key in h:
            h[key] = int(number(h[key], 1)) * f
    return out.astype(np.float32), h


def gaussian(data, header, sigma=1.5):
    from scipy.ndimage import gaussian_filter

    return gaussian_filter(np.nan_to_num(data, nan=float(np.nanmedian(data))), sigma).astype(np.float32), header.copy()


def median(data, header, size=3):
    from scipy.ndimage import median_filter

    return median_filter(data, size=int(size)).astype(np.float32), header.copy()


def unsharp(data, header, sigma=2.0, amount=1.0):
    smooth, _ = gaussian(data, header, sigma)
    return (data + amount * (data - smooth)).astype(np.float32), header.copy()


KERNELS = {
    "lowpass": np.full((3, 3), 1 / 9),
    "highpass": np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]], float),  # sharpen: identity + Laplacian
    "laplacian": np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], float),
    "edge_x": np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], float),  # Sobel: vertical edges
    "edge_y": np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], float),  # Sobel: horizontal edges
}


def kernel_filter(data, header, kind="lowpass"):
    """3 x 3 convolution (MaxIm's kernel filters); "sobel" is the edge strength sqrt(gx^2 + gy^2)."""
    from scipy.ndimage import convolve

    d = np.nan_to_num(np.asarray(data, float), nan=float(np.nanmedian(data)))
    if kind == "sobel":
        out = np.hypot(convolve(d, KERNELS["edge_x"], mode="nearest"), convolve(d, KERNELS["edge_y"], mode="nearest"))
    else:
        out = convolve(d, KERNELS[kind], mode="nearest")
    return out.astype(np.float32), header.copy()


def gaussian_psf(fwhm, size=None):
    sigma = fwhm / 2.3548
    half = int(np.ceil(4 * sigma)) if size is None else size // 2
    y, x = np.mgrid[-half : half + 1, -half : half + 1]
    psf = np.exp(-(x * x + y * y) / (2 * sigma * sigma))
    return psf / psf.sum()


def deconvolve(data, header, fwhm=3.0, iterations=20):
    """Richardson-Lucy deconvolution (Richardson 1972, Lucy 1974) with a Gaussian PSF of the given FWHM
    (pixels; measure it on the stars). The image is shifted to be positive first and back afterwards, so
    the sky level and the total counts are kept. More iterations sharpen more and amplify noise."""
    from scipy.ndimage import gaussian_filter

    d = np.nan_to_num(np.asarray(data, float), nan=float(np.nanmedian(data)))
    floor = float(d.min()) - 1.0
    d = d - floor
    sigma = fwhm / 2.3548

    def blur(a):  # the Gaussian PSF (symmetric: it is its own mirror), separable: 2400 x 2400 x 20 iterations
        return gaussian_filter(a, sigma, mode="constant", truncate=4.0)  # took 80 s as two FFTs per iteration

    u = np.full_like(d, d.mean())
    for _ in range(int(iterations)):
        u *= blur(d / np.maximum(blur(u), 1e-12))
    return (u + floor).astype(np.float32), header.copy()


def match_histogram(data, header, reference):
    """Histogram specification (MaxIm DL): each pixel value is replaced by the value at the same rank (quantile)
    in the reference image, so the result has the reference's brightness distribution — e.g. to give frames of
    a mosaic or an animation the same look. For display and comparison, not for measuring."""
    from .fits import read_image

    ref = np.asarray(read_image(reference)[0], np.float64)
    ref = np.sort(ref[np.isfinite(ref)])
    d = np.asarray(data, np.float64)
    good = np.isfinite(d)
    if not ref.size or not good.any():
        raise ValueError("the image has no valid pixels")
    order = np.argsort(d[good])  # ties keep any order: equal values get neighbouring quantiles either way
    n, m = order.size, ref.size
    # rank k sits at quantile (k + 0.5) / n, i.e. at position (k + 0.5) m / n - 0.5 of the sorted reference: both
    # grids are even, so the interpolation is direct (np.interp's search took 5.5 s of 7.8 on 2400 x 2400)
    pos = np.clip((np.arange(n) + 0.5) * (m / n) - 0.5, 0, m - 1)
    i = np.minimum(pos.astype(np.int64), max(m - 2, 0))
    j = np.minimum(i + 1, m - 1)
    ranked = np.empty(n)
    ranked[order] = ref[i] + (pos - i) * (ref[j] - ref[i])
    out = np.full(d.shape, np.nan)
    out[good] = ranked
    return out.astype(np.float32), header.copy()


def ddp(data, header, background=None, breakpoint=None, sigma=2.0):
    """Digital development processing (Okano 1997): out = a x / (blur(x) + a), x = data - background.
    Faint parts (x << a) stay linear, bright parts are compressed, so star cores and nebula show together.
    Defaults: background = median, break point a = the median of the pixels above the background."""
    from scipy.ndimage import gaussian_filter

    d = np.nan_to_num(np.asarray(data, float), nan=float(np.nanmedian(data)))
    b = float(np.median(d)) if background is None else float(background)
    x = np.clip(d - b, 0, None)
    a = float(np.median(x[x > 0])) if breakpoint is None and (x > 0).any() else float(breakpoint or 1.0)
    return (a * x / (gaussian_filter(x, sigma) + a)).astype(np.float32), header.copy()


def subtract_background(data, header, box=64, degree=2):
    """Remove a smooth background (light pollution, gradients): sigma-clipped medians in boxes, a 2-D
    polynomial of the given degree fitted to them at the box centres with clipping (boxes holding
    galaxies or bright stars are rejected), subtracted from the image."""
    from astropy.stats import sigma_clipped_stats

    ny, nx = data.shape
    box = int(max(4, min(box, ny, nx)))
    xs, ys, vs = [], [], []
    for y0 in range(0, ny - box + 1, box):
        for x0 in range(0, nx - box + 1, box):
            _, med, _ = sigma_clipped_stats(data[y0 : y0 + box, x0 : x0 + box], sigma=3.0)
            if np.isfinite(med):
                xs.append(x0 + (box - 1) / 2)
                ys.append(y0 + (box - 1) / 2)
                vs.append(med)
    xs, ys, vs = (np.asarray(a, float) for a in (xs, ys, vs))
    terms = [(i, j) for i in range(degree + 1) for j in range(degree + 1 - i)]
    if len(vs) < len(terms) + 2:
        raise ValueError("image too small for this box size")
    u, v = xs / nx, ys / ny  # scaled: well-conditioned
    a = np.column_stack([u**i * v**j for i, j in terms])
    keep = np.ones(len(vs), bool)
    for _ in range(5):
        coef = np.linalg.lstsq(a[keep], vs[keep], rcond=None)[0]
        r = vs - a @ coef
        sd = 1.4826 * np.median(np.abs(r[keep] - np.median(r[keep])))
        new = np.abs(r) < 3 * max(sd, 1e-12)
        if np.array_equal(new, keep) or new.sum() < len(terms) + 2:
            break
        keep = new
    yy, xx = np.mgrid[:ny, :nx]
    model = sum(c * (xx / nx) ** i * (yy / ny) ** j for c, (i, j) in zip(coef, terms, strict=True))
    return (data - model).astype(np.float32), header.copy()


def pixel_math(expression, images: dict, header):
    """Expression over named images (A is the current one), e.g. "A - 0.98 * B"."""
    from ..remotesensing.analysis import evaluate

    shapes = {np.shape(v) for v in images.values()}
    if len(shapes) > 1:
        raise ValueError(
            "the images do not have the same size: use frames of one camera and binning, or crop / bin them first"
        )
    return evaluate(expression, images), header.copy()


OPERATIONS = {
    "flip": flip,
    "rotate90": rotate90,
    "rotate": rotate,
    "resample": resample,
    "crop": crop,
    "bin": bin_image,
    "gaussian": gaussian,
    "median": median,
    "unsharp": unsharp,
    "background": subtract_background,
    "kernel": kernel_filter,
    "deconvolve": deconvolve,
    "ddp": ddp,
    "histogram_match": match_histogram,
}


def history(header, text):
    h = header.copy() if isinstance(header, fits.Header) else fits.Header(header)
    h.add_history(text[:70])
    return h


def colour_image(red, green, blue, stretch=0.5, q=8.0, align=True):
    """Three frames (2-D arrays, red / green / blue filters) -> uint8 RGB [y, x, 3], row 0 at the top.

    The green and blue frames are aligned on the red one (translation), each channel's sky is subtracted
    and the channels are scaled to the same level, then the asinh stretch of Lupton et al. 2004 (PASP 116,
    133) keeps the star colours where a per-channel stretch would turn bright stars white."""
    from astropy.stats import sigma_clipped_stats
    from astropy.visualization import make_lupton_rgb
    from scipy.ndimage import shift as move

    from ..photometry.aperture import frame_shift

    chans = [np.nan_to_num(np.asarray(c, np.float32)) for c in (red, green, blue)]
    if align:
        for i in (1, 2):
            dx, dy = frame_shift(chans[0], chans[i])
            chans[i] = move(chans[i], (-dy, -dx), order=1, mode="nearest")
    scaled = []
    for c in chans:
        _, med, std = sigma_clipped_stats(c[::2, ::2])
        c = c - med
        top = np.percentile(c, 99.9)
        scaled.append(c / (top if top > 0 else 1.0))
    rgb = make_lupton_rgb(*scaled, minimum=0.0, stretch=stretch, Q=q)
    return rgb[::-1]  # FITS row 0 is the bottom of the picture
