"""Combining a stack of frames with the rejections of the reference programs (plans/calibration.md CAL-5): IRAF
imcombine's minmax, ccdclip, crreject, avsigclip and pclip, Siril's linear-fit clipping and the generalised ESD
test (Rosner 1983). The stack is (n, ny, nx), already scaled; every method returns (combined image, frames kept
per pixel). nkeep: at least that many frames stay in every pixel (the extreme ones are given back first).

    image, kept = combine(stack, "ccdclip", gain=1.5, read_noise=6.0)
"""

import numpy as np
from scipy import stats


def _finish(stack, keep, nkeep, centre="mean"):
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
    image = np.nanmedian(vals, axis=0) if centre == "median" else np.nanmean(vals, axis=0)
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


METHODS = {"minmax": minmax, "ccdclip": ccdclip, "crreject": crreject, "avsigclip": avsigclip, "pclip": pclip,
           "linear_fit": linear_fit, "gesd": gesd, "none": lambda stack: np.ones(stack.shape, bool)}  # fmt: skip


def combine(stack, method="none", nkeep=1, centre="mean", **params):
    """(image, frames kept per pixel) of the stack with the method's rejection."""
    stack = np.asarray(stack, float)
    if method not in METHODS:
        raise ValueError(f"unknown rejection {method}")
    keep = METHODS[method](stack, **params)
    return _finish(stack, keep, nkeep, centre)
