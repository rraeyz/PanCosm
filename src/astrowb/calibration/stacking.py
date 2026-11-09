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

import json
import warnings
from pathlib import Path

import numpy as np
from astropy.io import fits
from scipy.ndimage import map_coordinates

from ..compute.combine import clipped_mean
from ..compute.stack import gpu_combine
from ..io.fits import find_image_hdu
from ..io.lzw import readable
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
    known, keys = _shift_cache(), _pair_keys(paths, binning)
    # the same frames again (comparisons, then the light curve, other radii; the quality check writes them too):
    # only pairs not known yet are measured, e.g. around frames left out after the quality check
    missing = [i for i, k in enumerate(keys) if k not in known]
    if missing:
        stretches, start = [], missing[0]  # consecutive missing pairs i..j need frames i..j + 1
        for a, b in zip(missing, [*missing[1:], None], strict=True):
            if b != a + 1:
                stretches.append((start, a))
                start = b
        n = max(1, min(4 * workers(), len(missing) // 8))  # runs of at least 8 frames: each reads one frame twice
        runs = []
        for i, j in stretches:
            pieces = max(1, round(n * (j - i + 1) / len(missing)))
            edges = np.linspace(i, j + 1, pieces + 1).round().astype(int)
            runs += [(a, b) for a, b in zip(edges[:-1], edges[1:], strict=True) if b > a]
        found = pmap(_run_shifts, [(paths[a : b + 1], binning) for a, b in runs], ctx, "aligning", min_items=2)
        new = {keys[a + k]: [float(x), float(y)] for (a, _), shifts in zip(runs, found, strict=True)
               for k, (x, y) in enumerate(shifts)}  # fmt: skip
        known = _save_shifts(known, new)
    steps = [known[k] for k in keys]
    return [(0.0, 0.0), *(tuple(x) for x in np.cumsum(steps, axis=0).tolist())]


SHIFT_CACHE_PAIRS = 20_000  # ~4 MB of JSON; the oldest pairs go first


def _pair_keys(paths, binning):
    """One key per consecutive pair: both files as they are now (path, size, modification time) and the binning."""
    stamps = []
    for p in paths:
        st = Path(p).stat()
        stamps.append(f"{Path(p).resolve()}|{st.st_size}|{st.st_mtime_ns}")
    return [f"{binning}|{a}|{b}" for a, b in zip(stamps, stamps[1:], strict=False)]


def _shift_cache():
    from ..settings import config_dir

    try:
        return json.loads((config_dir() / "shifts.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_shifts(known, new):
    from ..settings import config_dir

    merged = {k: v for k, v in known.items() if k not in new} | new
    kept = dict(list(merged.items())[-SHIFT_CACHE_PAIRS:])
    path = config_dir() / "shifts.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        tmp.write_text(json.dumps(kept), encoding="utf-8")
        tmp.replace(path)
    except OSError:  # a read-only settings folder: the shifts are only not kept
        pass
    return merged  # everything known now, the new pairs included even beyond the cap


def _run_shifts(run):
    """Shifts between consecutive frames of a run (paths, binning)."""
    from ..photometry.aperture import bin_frame

    paths, binning = run

    def frame(p):  # only the binned frame is kept: a 4k x 4k frame is freed as soon as it is read (item 9b)
        data = load(p)[0]
        return bin_frame(data, binning) if binning > 1 else data

    prev = frame(paths[0])
    out = []
    for p in paths[1:]:
        data = frame(p)
        dx, dy = frame_shift(prev, data, 1)
        out.append((binning * dx, binning * dy))
        prev = data
    return out


METHODS = ("mean", "median", "sum")
REJECTIONS = ("none", "sigma", "mad", "winsorized", "minmax", "percentile")
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
    if rejection == "sigma":  # IRAF's sigclip where 10+ frames cover the pixel; median / MAD where fewer do
        n = keep.sum(axis=0)
        out = _iraf_sigclip(block, keep, sigma, sigma)
        few = (n > 0) & (n < IRAF_MIN_FRAMES)
        if few.any():
            out[:, few] = reject(block[:, few], "mad", sigma, low, high, iterations)
        return out
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


# With n values the rms about their median can never put one outlier more than sqrt(n - 1) sigma away: below 10
# frames a cosmic ray in one frame is never 3 sigma off (7 frames: 2.45), so IRAF's help sends few images to other
# algorithms; there the median / MAD clipping, which rejects it.
IRAF_MIN_FRAMES = 10


def _iraf_sigclip(block, keep, lsigma, hsigma, min_clip=3):
    """IRAF imcombine's sigma clipping about the median (reject=sigclip, mclip=yes: ic_msigclip in
    images/immatch/src/imcombine/src/icsclip.gx). Each pixel's values are sorted once; the centre is the median of
    the values still kept and sigma their rms about it (n - 1); values more than lsigma below or hsigma above go,
    from the ends of the sorted run, until nothing changes or fewer than three are left. On sorted values every
    rejection narrows a window, so one sort serves every iteration (median / MAD clipping sorted ten times, and
    its spread from 40 values rejected good ones: the stack's noise came out 1.6 % above IRAF's)."""
    s = np.sort(block, axis=0)  # NaN last
    n = keep.sum(axis=0)
    zero = np.zeros((1, *block.shape[1:]))
    finite = np.nan_to_num(s.astype(np.float64))
    c1 = np.concatenate([zero, np.cumsum(finite, axis=0)])  # window sums from cumulative sums
    c2 = np.concatenate([zero, np.cumsum(finite * finite, axis=0)])
    del finite
    lo, hi = np.zeros(n.shape, np.intp), n.astype(np.intp)

    def at(a, i):
        return np.take_along_axis(a, i[None], 0)[0]

    with np.errstate(invalid="ignore", divide="ignore"):
        while True:
            m = hi - lo
            active = m >= min_clip
            if not active.any():
                break
            i1, i2 = lo + np.maximum(m - 1, 0) // 2, lo + m // 2
            med = (at(s, np.minimum(i1, len(s) - 1)).astype(np.float64) + at(s, np.minimum(i2, len(s) - 1))) / 2
            s1, s2 = at(c1, hi) - at(c1, lo), at(c2, hi) - at(c2, lo)
            sd = np.sqrt(np.maximum(s2 - 2 * med * s1 + m * med * med, 0) / np.maximum(m - 1, 1))
            go = active & (sd > 0)
            below = np.count_nonzero(s < (med - lsigma * sd), axis=0)  # the sorted run's first values
            above = np.count_nonzero(s > (med + hsigma * sd), axis=0)  # its last finite values (NaN compare false)
            new_lo = np.where(go, np.maximum(lo, below), lo)
            new_hi = np.where(go, np.maximum(np.minimum(hi, n - above), new_lo), hi)
            if np.array_equal(new_lo, lo) and np.array_equal(new_hi, hi):
                break
            lo, hi = new_lo, new_hi
        first = at(s, np.minimum(lo, len(s) - 1))
        last = at(s, np.maximum(hi - 1, 0))
        return keep & (hi > lo) & (block >= first) & (block <= last)


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
    paths, transforms, (fast, method, rejection, sigma, low, high, scale, shift, weights, budget, on_gpu), r0, r1 = job
    hduls = [fits.open(readable(p)) for p in paths]
    try:
        hdus = [h[find_image_hdu(h)] for h in hduls]
        ny, nx = hdus[0].shape[-2:]
        # masks and sorts need more; IRAF's clipping also a sorted copy and two float64 running sums
        factor = 1 if fast or on_gpu else 8 if rejection == "sigma" else 4
        rows = max(1, budget // (len(paths) * nx * 4 * factor))
        out, cnt = np.empty((r1 - r0, nx), np.float32), np.empty((r1 - r0, nx), np.int32)
        xs = np.arange(nx, dtype=np.float64)
        for b0 in range(r0, r1, rows):
            b1 = min(r1, b0 + rows)
            yy0, xx0 = np.meshgrid(np.arange(b0, b1, dtype=np.float64), xs, indexing="ij")
            block = []
            for hdu, (m, t) in zip(hdus, transforms, strict=True):
                if np.array_equal(m, np.eye(2)):  # a shift: the same two weights for every pixel
                    block.append(_shifted_rows(hdu, b0, b1, t, ny, nx))
                    continue
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
                out[b0 - r0 : b1 - r0] = clipped_mean(block, sigma, use_gpu=on_gpu)[0]
            else:
                block = block * scale[:, None, None].astype(np.float32) + shift[:, None, None].astype(np.float32)
                args = (method, rejection, sigma, low, high, weights)
                done = gpu_combine(block, *args, force=True) if on_gpu else None
                if done is None and not on_gpu:
                    done = combine(block, *args)
                elif done is None:  # a GPU failure: the CPU in quarters of rows, within the memory budget
                    cuts = np.linspace(0, b1 - b0, 5).astype(int)
                    done = np.concatenate(
                        [combine(block[:, a:b], *args) for a, b in zip(cuts[:-1], cuts[1:], strict=True) if b > a]
                    )
                out[b0 - r0 : b1 - r0] = done
            cnt[b0 - r0 : b1 - r0] = np.isfinite(block).sum(axis=0)  # coverage: frames that cover the pixel
    finally:
        for h in hduls:
            h.close()
    return out, cnt


def _shifted_rows(hdu, b0, b1, t, ny, nx):
    """Rows b0..b1 of the frame shifted by t = (dx, dy): value at (x + dx, y + dy), bilinear, NaN outside the frame -
    map_coordinates(order=1, cval=nan) for a translation, from four shifted slices (it took a third of a stack's
    time computing the same weights for every pixel)."""
    dx, dy = float(t[0]), float(t[1])
    ix, iy = int(np.floor(dx)), int(np.floor(dy))
    fx, fy = dx - ix, dy - iy
    out = np.full((b1 - b0, nx), np.nan)
    ys = np.arange(b0, b1) + iy  # source rows (and the next one)
    xs = np.arange(nx) + ix
    lo, hi = max(ys[0], 0), min(ys[-1] + 2, ny)
    if hi <= lo:
        return out.astype(np.float32)
    sub = np.asarray(hdu.section[lo:hi, :], dtype=np.float64)

    def take(yv, xv):  # sub at (row yv, column xv), NaN outside
        ok = ((yv >= 0) & (yv < ny))[:, None] & ((xv >= 0) & (xv < nx))[None, :]
        v = sub[np.clip(yv - lo, 0, len(sub) - 1)][:, np.clip(xv, 0, nx - 1)]
        return np.where(ok, v, np.nan)

    # a point exactly on the last row / column takes no weight from beyond it (map_coordinates' rule)
    out = take(ys, xs) * ((1 - fy) * (1 - fx))
    if fx:
        out += take(ys, xs + 1) * ((1 - fy) * fx)
    if fy:
        out += take(ys + 1, xs) * (fy * (1 - fx))
    if fx and fy:
        out += take(ys + 1, xs + 1) * (fy * fx)
    return out.astype(np.float32)


def _gpu_combine_wanted(n_frames, pixels):
    """Whether a band of the stack goes to the GPU: compute mode and device, at most 128 frames, enough work."""
    from ..compute import device
    from ..compute.stack import GPU_MIN_VALUES, MAX_FRAMES

    return n_frames <= MAX_FRAMES and n_frames * pixels >= GPU_MIN_VALUES and device() is not None


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
    # the masters' clipped mean (median / MAD, GPU-ready): the old default, now "mad"
    fast = (method, rejection, normalize, weighting) == ("mean", "mad", "none", "none")
    stats = frame_stats(paths) if normalize != "none" or weighting != "none" else None
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

    with fits.open(readable(paths[0])) as h0:
        hdu0 = h0[find_image_hdu(h0)]
        ny, nx = hdu0.shape[-2:]
        header = hdu0.header.copy()
    # bands of rows on every core, each with its share of the memory budget (the same memory in all): a 40-frame
    # LCO stack took 59 s on one core
    n = min(workers(), max(1, ny // 64)) if len(paths) * ny * nx > 50_000_000 else 1
    edges = np.linspace(0, ny, 2 * n + 1).round().astype(int)
    # decided here once: the bands do not each look for a GPU (0.4 s per process without one)
    on_gpu = _gpu_combine_wanted(len(paths), (edges[1] - edges[0]) * nx)
    how = (fast, method, rejection, sigma, low, high, scale, shift, weights, STACK_BUDGET // n, on_gpu)
    jobs = [(paths, transforms, how, a, b) for a, b in zip(edges[:-1], edges[1:], strict=True) if b > a]
    parts = pmap(_stack_band, jobs, ctx, "stacking", min_items=2)
    out = np.concatenate([o for o, _ in parts])
    cnt = np.concatenate([c for _, c in parts])
    header["NCOMBINE"] = (len(paths), "frames stacked")
    how = {"sigma": "IRAF sigclip, MAD below 10 frames", "mad": "median / MAD"}.get(rejection, rejection)
    header["STACKMTH"] = (f"{method}, {how} rejection", "stack method")
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
