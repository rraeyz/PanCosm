"""Align frames (translation) and combine them with robust sigma clipping.

Offsets are found frame to frame (FFT cross-correlation on despiked frames) and accumulated,
so slowly drifting fields stay aligned. The output is built in row blocks: from every frame
only the rows a block needs are read and resampled (bilinear, sub-pixel), so a stack never has
to fit in memory. Pixels not covered by a frame are NaN in that frame and ignored by the
combine; the coverage count is written as a second image extension.

Alignment: by translation (FFT cross-correlation, frame to frame) or, for frames that are rotated or scaled
(meridian flip, alt-az mount, another telescope), by star-pattern matching (calibration/starmatch.py): each
frame's transform from the first frame's pixels is then a rotation, a scale and a shift.

Combining (as Siril / PixInsight / MaxIm DL offer it), per pixel over the frames that cover it:
- normalisation: none, additive (each frame's sky median shifted to the first frame's) or multiplicative
  (scaled to it); the sky median and noise of every frame come from a sigma-clipped subsample;
- rejection: none; sigma (median +- sigma x MAD-std, iterated); winsorized sigma (the spread from values pulled
  in to median +- 1.5 sigma, Huber's estimator, then median +- sigma x that); min-max (the n lowest and the n
  highest dropped); percentile (outside median x (1 - low) .. median x (1 + high), Siril's percentile clipping);
- combination: mean (weighted, weights 1 / noise^2 of each normalised frame when "noise" weighting is chosen),
  median, or sum (the mean times the number of frames, so partly covered pixels keep the right level).
"""

import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from scipy.ndimage import map_coordinates

from ..compute.combine import clipped_mean
from ..io.fits import find_image_hdu
from ..photometry.aperture import frame_shift
from .masters import load

# bytes per block of a stack, shared by the bands: 512 MB used 2.3 GB on 40 LCO frames, 128 MB 1.5 GB and was faster
# (IRAF imcombine on the same frames: 9.6 s, 0.42 GB; ours 9.7 s)
STACK_BUDGET = 128 * 2**20


def align_offsets(paths, ctx=None, binning=1):
    """(dx, dy) of every frame relative to the first: position in frame i = position in frame 0 + offset.
    binning > 1: shifts from binned frames (a tenth of a binned pixel; for checks, not for stacking). The shifts
    between consecutive frames are independent, so runs of frames go to every core (265 LCO frames: decompressing
    and correlating took 37 s on one)."""
    from ..engine.parallel import pmap, workers

    paths = [str(p) for p in paths]
    if len(paths) < 2:
        return [(0.0, 0.0)]
    n = max(1, min(4 * workers(), len(paths) // 8))  # runs of at least 8 frames: each run reads one frame twice
    edges = np.linspace(0, len(paths) - 1, n + 1).round().astype(int)
    runs = [(paths[a : b + 1], binning) for a, b in zip(edges[:-1], edges[1:], strict=True) if b > a]
    steps = [s for run in pmap(_run_shifts, runs, ctx, "aligning", min_items=2) for s in run]
    return [(0.0, 0.0), *(tuple(x) for x in np.cumsum(steps, axis=0).tolist())]


def _run_shifts(run):
    """Shifts between consecutive frames of a run (paths, binning)."""
    paths, binning = run
    prev, _ = load(paths[0])
    out = []
    for p in paths[1:]:
        data, _ = load(p)
        out.append(frame_shift(prev, data, binning))
        prev = data
    return out


METHODS = ("mean", "median", "sum")
REJECTIONS = ("none", "sigma", "winsorized", "minmax", "percentile")
NORMALISATIONS = ("none", "additive", "multiplicative")
WEIGHTINGS = ("none", "noise")


def align_transforms(paths, method="translation", ctx=None):
    """(M, t) of every frame: position in frame i = M @ position in frame 0 + t."""
    if method == "translation":
        return [(np.eye(2), np.asarray(o, float)) for o in align_offsets(paths, ctx)]
    from . import starmatch

    ref = starmatch.stars(load(paths[0])[0])
    out = [(np.eye(2), np.zeros(2))]
    for i, p in enumerate(paths[1:], 1):
        if ctx:
            ctx.check()
            ctx.progress(0.3 * i / len(paths), "aligning")
        m, t, _, _ = starmatch.match(ref, starmatch.stars(load(p)[0]))
        out.append((m, t))
    return out


def frame_stats(paths):
    """Sky median and noise (sigma-clipped, on every 4th pixel) of each frame (frames on every core)."""
    from ..engine.parallel import pmap

    return pmap(_frame_stat, [str(p) for p in paths])


def _frame_stat(path):
    from astropy.stats import sigma_clipped_stats

    data, _ = load(path)
    _, med, std = sigma_clipped_stats(data[::4, ::4])
    return float(med), float(std)


def _median0(v):
    """np.nanmedian(v, axis=0) from one sort (NaN sorts last): numpy's nanmedian over a few frames goes through masked
    arrays, 30 of 53 s of stacking 16 LCO frames."""
    s = np.sort(v, axis=0)
    n = np.count_nonzero(~np.isnan(v), axis=0)
    lo, hi = np.maximum((n - 1) // 2, 0), np.maximum(n // 2, 0)
    m = (np.take_along_axis(s, lo[None], 0)[0] + np.take_along_axis(s, hi[None], 0)[0]) / 2
    return np.where(n > 0, m, np.nan)


def reject(block, rejection="sigma", sigma=3.0, low=1, high=1, iterations=5):
    """Mask of the values kept (finite and not rejected), block = frames x rows x columns."""
    keep = np.isfinite(block)
    if rejection == "none":
        return keep
    if rejection == "minmax":  # the `low` lowest and `high` highest finite values of each pixel
        n = keep.sum(axis=0)
        rank = np.argsort(np.argsort(np.where(keep, block, np.inf), axis=0), axis=0)
        return keep & (rank >= low) & (rank < n - high)
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        if rejection == "percentile":
            med = _median0(np.where(keep, block, np.nan))
            return keep & (block >= med * (1 - low)) & (block <= med * (1 + high))
        for _ in range(iterations):
            vals = np.where(keep, block, np.nan)
            med = _median0(vals)
            spread = 1.4826 * _median0(np.abs(vals - med))
            if rejection == "winsorized":
                for _ in range(5):  # Huber: values beyond 1.5 sigma pulled in, spread measured again
                    w = np.clip(vals, med - 1.5 * spread, med + 1.5 * spread)
                    spread = 1.134 * np.nanstd(w, axis=0)  # 1.134: the winsorized std of a Gaussian is 0.88 sigma
            new = keep & (np.abs(block - med) <= sigma * np.maximum(spread, 1e-12))
            if np.array_equal(new, keep):
                break
            keep = new
    return keep


def combine(block, method="mean", rejection="sigma", sigma=3.0, low=1, high=1, weights=None):
    """One value per pixel from the frames' values in block (NaN where a frame does not cover the pixel)."""
    keep = reject(block, rejection, sigma, low, high)
    vals = np.where(keep, block, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        if method == "median":
            return _median0(vals).astype(np.float32)
        w = np.ones(len(block)) if weights is None else np.asarray(weights, float)
        w = np.where(keep, w[:, None, None], 0.0)
        mean = np.nansum(np.nan_to_num(vals) * w, axis=0) / w.sum(axis=0)
        return (mean * len(block) if method == "sum" else mean).astype(np.float32)


def _stack_band(job):
    """Rows r0..r1 of a stack: (image, coverage) of that band, block by block within its memory budget."""
    paths, transforms, (fast, method, rejection, sigma, low, high, scale, shift, weights, budget), r0, r1 = job
    hduls = [fits.open(p) for p in paths]
    try:
        hdus = [h[find_image_hdu(h)] for h in hduls]
        ny, nx = hdus[0].shape[-2:]
        rows = max(1, budget // (len(paths) * nx * 4 * (1 if fast else 4)))  # masks and sorts need more
        out, cnt = np.empty((r1 - r0, nx), np.float32), np.empty((r1 - r0, nx), np.int32)
        xs = np.arange(nx, dtype=np.float64)
        for b0 in range(r0, r1, rows):
            b1 = min(r1, b0 + rows)
            yy0, xx0 = np.meshgrid(np.arange(b0, b1, dtype=np.float64), xs, indexing="ij")
            block = []
            for hdu, (m, t) in zip(hdus, transforms, strict=True):
                xsrc = m[0, 0] * xx0 + m[0, 1] * yy0 + t[0]
                ysrc = m[1, 0] * xx0 + m[1, 1] * yy0 + t[1]
                lo, hi = int(np.floor(ysrc.min())) - 1, int(np.ceil(ysrc.max())) + 2
                lo_c, hi_c = max(lo, 0), min(hi, ny)
                if hi_c <= lo_c:
                    block.append(np.full((b1 - b0, nx), np.nan, np.float32))
                    continue
                sub = np.asarray(hdu.section[lo_c:hi_c, :], dtype=np.float32)
                block.append(map_coordinates(sub, [ysrc - lo_c, xsrc], order=1, cval=np.nan, prefilter=False))
            block = np.stack(block)
            if fast:
                out[b0 - r0 : b1 - r0] = clipped_mean(block, sigma)[0]
            else:
                block = block * scale[:, None, None].astype(np.float32) + shift[:, None, None].astype(np.float32)
                out[b0 - r0 : b1 - r0] = combine(block, method, rejection, sigma, low, high, weights)
            cnt[b0 - r0 : b1 - r0] = np.isfinite(block).sum(axis=0)  # coverage: frames that cover the pixel
    finally:
        for h in hduls:
            h.close()
    return out, cnt


def stack(
    paths,
    offsets=None,
    sigma=3.0,
    align="translation",
    ctx=None,
    method="mean",
    rejection="sigma",
    low=1,
    high=1,
    normalize="none",
    weighting="none",
):
    """Return (image, coverage = number of frames covering each pixel, header of the first frame)."""
    paths = [str(p) for p in paths]
    if offsets:
        transforms = [(np.eye(2), np.asarray(o, float)) for o in offsets]
    else:
        transforms = align_transforms(paths, align, ctx)
    fast = (method, rejection, normalize, weighting) == ("mean", "sigma", "none", "none")  # GPU-ready default
    stats = None if fast else frame_stats(paths)
    scale, shift, weights = np.ones(len(paths)), np.zeros(len(paths)), None
    if stats:
        med = np.array([m for m, _ in stats])
        noise = np.array([n for _, n in stats])
        if normalize == "multiplicative":
            scale = med[0] / med
        elif normalize == "additive":
            shift = med[0] - med
        if weighting == "noise":
            weights = 1 / np.maximum(noise * scale, 1e-12) ** 2
            weights = weights / weights.mean()
    from ..engine.parallel import pmap, workers

    with fits.open(paths[0]) as h0:
        hdu0 = h0[find_image_hdu(h0)]
        ny, nx = hdu0.shape[-2:]
        header = hdu0.header.copy()
    # bands of rows on every core, each with its share of the memory budget (the same memory in all): a 40-frame
    # LCO stack took 59 s on one core
    n = min(workers(), max(1, ny // 64)) if len(paths) * ny * nx > 50_000_000 else 1
    edges = np.linspace(0, ny, 2 * n + 1).round().astype(int)
    how = (fast, method, rejection, sigma, low, high, scale, shift, weights, STACK_BUDGET // n)
    jobs = [(paths, transforms, how, a, b) for a, b in zip(edges[:-1], edges[1:], strict=True) if b > a]
    parts = pmap(_stack_band, jobs, ctx, "stacking", min_items=2)
    out = np.concatenate([o for o, _ in parts])
    cnt = np.concatenate([c for _, c in parts])
    header["NCOMBINE"] = (len(paths), "frames stacked")
    header["STACKMTH"] = (f"{method}, {rejection} rejection", "stack method")
    header["STACKNRM"] = (normalize, "normalisation before stacking")
    header["STACKWGT"] = (weighting, "frame weights")
    from .starmatch import describe

    for i, (p, (m, t)) in enumerate(zip(paths, transforms, strict=True)):
        w = f" w={weights[i]:.3f}" if weights is not None else ""
        angle, scale = describe(m)
        turn = f" rot={angle:+.2f} scale={scale:.4f}" if abs(angle) > 1e-6 or abs(scale - 1) > 1e-9 else ""
        header.add_history(f"stacked {Path(p).name} dx={t[0]:+.2f} dy={t[1]:+.2f}{turn}{w}")
    return out, cnt, header


def save_stack(path, image, count, header):
    fits.HDUList([fits.PrimaryHDU(image, header), fits.ImageHDU(count.astype(np.int16), name="COVERAGE")]).writeto(
        path, overwrite=True, output_verify="silentfix"
    )
    return str(path)
