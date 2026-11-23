"""Combining a stack of frames with the rejections of the reference programs (plans/calibration.md CAL-5): IRAF
imcombine's minmax, ccdclip, crreject, avsigclip and pclip, Siril's linear-fit clipping and the generalised ESD
test (Rosner 1983). The stack is (n, ny, nx), already scaled; every method returns (combined image, frames kept
per pixel). nkeep: at least that many frames stay in every pixel (the extreme ones are given back first).

    image, kept = combine(stack, "ccdclip", gain=1.5, read_noise=6.0)
"""

import numpy as np
from scipy import ndimage, stats

from ..core.errors import AppError


def _finish(stack, keep, nkeep, centre="mean", weights=None):
    """Combine the kept values; where fewer than nkeep stayed, the nkeep closest to the median are used."""
    keep = keep.copy()
    short = keep.sum(axis=0) < nkeep
    if short.any():
        med = np.median(stack, axis=0)
        order = np.argsort(np.abs(stack - med), axis=0)
        give = np.zeros_like(keep)
        np.put_along_axis(give, order[:nkeep], True, axis=0)
        keep[:, short] = give[:, short]
    vals = np.where(keep, stack, np.nan)
    if centre == "median":
        image = np.nanmedian(vals, axis=0)
    elif weights is None:
        image = np.nanmean(vals, axis=0)
    else:
        w = np.asarray(weights, float)[:, None, None] * keep
        image = (np.where(keep, stack, 0) * w).sum(axis=0) / w.sum(axis=0)
    return image.astype(np.float32), keep.sum(axis=0).astype(np.int16)


def minmax(stack, nlow=1, nhigh=1):
    order = np.argsort(stack, axis=0)
    n = len(stack)
    keep = np.zeros(stack.shape, bool)
    np.put_along_axis(keep, order[nlow : n - nhigh], True, axis=0)
    return keep


def _noise_clip(stack, sigma_of, lsigma, hsigma, iterations=10):
    """Iterative clipping about the median of the kept values with σ from a model of the centre (mclip yes)."""
    keep = np.ones(stack.shape, bool)
    for _ in range(iterations):
        centre = np.nanmedian(np.where(keep, stack, np.nan), axis=0)
        s = sigma_of(centre)
        new = (stack >= centre - lsigma * s) & (stack <= centre + hsigma * s)
        if np.array_equal(new, keep):
            break
        keep = new
    return keep


def sigclip(stack, lsigma=3.0, hsigma=3.0, iterations=10):
    """Iterative clipping about the median of the kept values with σ = 1.4826 MAD of them (an rms scale cannot
    reject one hit among fewer than 10 frames: it never lies more than √(n−1) σ away). np.inf: that side is kept."""
    keep = np.ones(stack.shape, bool)
    for _ in range(iterations):
        vals = np.where(keep, stack, np.nan)
        centre = np.nanmedian(vals, axis=0)
        s = 1.4826 * np.nanmedian(np.abs(vals - centre), axis=0)
        lo = -np.inf if np.isinf(lsigma) else centre - lsigma * s
        hi = np.inf if np.isinf(hsigma) else centre + hsigma * s
        new = (stack >= lo) & (stack <= hi)
        if np.array_equal(new, keep):
            break
        keep = new
    return keep


def ccdclip(stack, gain=1.0, read_noise=0.0, snoise=0.0, lsigma=3.0, hsigma=3.0):
    """σ from the CCD noise model (ADU): √((rn/g)² + max(c, 0)/g + (snoise·c)²) about the centre c."""

    def sigma(c):
        return np.sqrt((read_noise / gain) ** 2 + np.clip(c, 0, None) / gain + (snoise * c) ** 2)

    return _noise_clip(stack, sigma, lsigma, hsigma)


def crreject(stack, gain=1.0, read_noise=0.0, snoise=0.0, hsigma=3.0):
    """ccdclip rejecting only high values (cosmic rays)."""
    return ccdclip(stack, gain, read_noise, snoise, lsigma=np.inf, hsigma=hsigma)


def avsigclip(stack, lsigma=3.0, hsigma=3.0):
    """σ ∝ √signal with the factor estimated per image line from all its pixels (IRAF avsigclip: right for few
    frames, where each pixel's own scatter is too poorly known)."""
    med = np.median(stack, axis=0)
    var = np.var(stack, axis=0, ddof=1)
    k = np.median(var / np.clip(med, 1e-9, None), axis=1, keepdims=True)  # per line (row)
    return _noise_clip(stack, lambda c: np.sqrt(k * np.clip(c, 1e-9, None)), lsigma, hsigma)


def pclip(stack, pclip=-0.5, lsigma=3.0, hsigma=3.0):
    """IRAF pclip: σ from the distance between the median and the value pclip of the way to the low (negative) or
    high (positive) end of the sorted stack."""
    s = np.sort(stack, axis=0)
    n = len(stack)
    mid = (n - 1) / 2
    j = int(np.clip(round(mid + pclip * mid), 0, n - 1))
    med = np.median(stack, axis=0)
    sigma = np.abs(s[j] - med)
    return (stack >= med - lsigma * sigma) & (stack <= med + hsigma * sigma)


def linear_fit(stack, lsigma=3.0, hsigma=3.0, iterations=5):
    """Siril's linear-fit clipping: a line through the sorted values of each pixel (robust to a gradient between
    frames); values off it by more than the residuals' σ are rejected."""
    n = len(stack)
    order = np.argsort(stack, axis=0)
    s = np.take_along_axis(stack, order, axis=0)
    i = np.arange(n, dtype=float)[:, None, None] * np.ones_like(s)
    keep_sorted = np.ones(s.shape, bool)
    for _ in range(iterations):
        w = keep_sorted.astype(float)
        sw, sx, sy = w.sum(0), (w * i).sum(0), (w * s).sum(0)
        sxx, sxy = (w * i * i).sum(0), (w * i * s).sum(0)
        den = np.where(sw * sxx - sx * sx == 0, 1.0, sw * sxx - sx * sx)
        b = (sw * sxy - sx * sy) / den
        a = (sy - b * sx) / np.maximum(sw, 1)
        res = s - (a + b * i)
        sig = np.sqrt((w * res**2).sum(0) / np.maximum(sw - 2, 1))
        new = (res >= -lsigma * sig) & (res <= hsigma * sig)
        if np.array_equal(new, keep_sorted):
            break
        keep_sorted = new
    keep = np.zeros(stack.shape, bool)
    np.put_along_axis(keep, order, keep_sorted, axis=0)
    return keep


def gesd(stack, max_outliers=None, alpha=0.05):
    """The generalised ESD test (Rosner 1983) per pixel: up to max_outliers (a third of the frames) are tested, the
    number rejected is the largest r whose statistic passes its critical value."""
    n = len(stack)
    r_max = max_outliers or max(1, n // 3)
    keep = np.ones(stack.shape, bool)
    removed = []  # per round: which frame index left, and whether R > λ
    passed_upto = np.zeros(stack.shape[1:], int)
    for r in range(1, r_max + 1):
        vals = np.where(keep, stack, np.nan)
        mean, sd = np.nanmean(vals, axis=0), np.nanstd(vals, axis=0, ddof=1)
        dev = np.abs(vals - mean) / np.where(sd > 0, sd, np.inf)
        dev = np.where(keep, dev, -1)
        worst = np.argmax(dev, axis=0)
        big = np.take_along_axis(dev, worst[None], axis=0)[0]
        m = n - r + 1
        p = 1 - alpha / (2 * m)
        t = stats.t.ppf(p, m - 2)
        lam = (m - 1) * t / np.sqrt((m - 2 + t * t) * m)
        passed_upto = np.where(big > lam, r, passed_upto)
        removed.append(worst)
        np.put_along_axis(keep, worst[None], False, axis=0)
    keep = np.ones(stack.shape, bool)
    for r, worst in enumerate(removed, start=1):
        drop = passed_upto >= r
        rows = np.zeros(stack.shape, bool)
        np.put_along_axis(rows, worst[None], True, axis=0)
        keep &= ~(rows & drop[None])
    return keep


METHODS = {"sigclip": sigclip, "minmax": minmax, "ccdclip": ccdclip, "crreject": crreject, "avsigclip": avsigclip,
           "pclip": pclip, "linear_fit": linear_fit, "gesd": gesd,
           "none": lambda stack: np.ones(stack.shape, bool)}  # fmt: skip


def _stat(frames, how):
    """One number per frame. "mode" is Pearson's 3·median − 2·mean (no histogram mode in the repo)."""
    flat = frames.reshape(len(frames), -1)
    if how == "median":
        return np.median(flat, axis=1)
    if how == "mean":
        return flat.mean(axis=1)
    if how == "mode":
        return 3 * np.median(flat, axis=1) - 2 * flat.mean(axis=1)
    raise AppError("unknown scaling {by}", by=how)


def _values(how, frames, exposure):
    """Per-frame numbers for a choice: a statistic over the region, the exposure times, or the values given
    (a header keyword read by the caller)."""
    if not isinstance(how, str):
        return np.asarray(how, float)
    if how == "exposure":
        if exposure is None:
            raise AppError("unknown scaling {by}", by=how)
        return np.asarray(exposure, float)
    return _stat(frames, how)


def scale_and_zero(stack, scale="none", zero="none", region=None, exposure=None):
    """IRAF imcombine's scale and zero. Multiplicative factors are normalised to the first frame (our choice: the
    repo does not state IRAF's normalisation), then the zero offsets, also relative to the first frame, are
    subtracted. scale, zero: none / mode / median / mean / exposure (scale only) / a sequence of per-frame
    values; statistics over region = (y0, y1, x0, x1) or the whole frame."""
    stack = np.asarray(stack, float)
    sl = np.s_[:, region[0] : region[1], region[2] : region[3]] if region else np.s_[:]
    if not (isinstance(scale, str) and scale == "none"):
        v = _values(scale, stack[sl], exposure)
        stack = stack * (v[0] / v)[:, None, None]
    if not (isinstance(zero, str) and zero == "none"):
        if isinstance(zero, str) and zero == "exposure":
            raise AppError("unknown scaling {by}", by=zero)
        z = _values(zero, stack[sl], exposure)
        stack = stack - (z - z[0])[:, None, None]
    return stack


def _noise_weights(stack, region):
    sub = stack[:, region[0] : region[1], region[2] : region[3]] if region else stack
    flat = sub.reshape(len(sub), -1)
    mad = np.median(np.abs(flat - np.median(flat, axis=1, keepdims=True)), axis=1)
    return 1.0 / (1.4826 * mad) ** 2


def combine(stack, method="none", nkeep=1, centre="mean", grow=0, scale="none", zero="none", weights="none",
            region=None, exposure=None, **params):  # fmt: skip
    """(image, frames kept per pixel) of the stack with the method's rejection.

    grow: a pixel within that many pixels (same frame) of a rejected one is rejected too (0 = off); nkeep is
    honoured after growing. scale, zero, region, exposure: see scale_and_zero (done first). weights: none /
    exposure / noise (1/σ², σ from the MAD of each frame over region, after scaling) / a sequence of per-frame
    values; they weight the mean only, the median ignores them."""
    stack = scale_and_zero(stack, scale, zero, region, exposure)
    if method not in METHODS:
        raise AppError("unknown rejection {method}", method=method)
    keep = METHODS[method](stack, **params)
    if grow > 0:
        r = int(np.ceil(grow))
        yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
        disc = yy**2 + xx**2 <= grow**2
        keep = ~np.array([ndimage.binary_dilation(~k, disc) for k in keep])
    w = None
    if not isinstance(weights, str):
        w = np.asarray(weights, float)
    elif weights == "exposure" and exposure is not None:
        w = np.asarray(exposure, float)
    elif weights == "noise":
        w = _noise_weights(stack, region)
    elif weights != "none":
        raise AppError("unknown weighting {by}", by=weights)
    return _finish(stack, keep, nkeep, centre, w)
