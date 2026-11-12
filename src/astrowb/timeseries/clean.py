"""Cleaning that does not eat the signal (plans/period.md PER-2): segments, detrending filters with a mask of
events, nightly means. Every function returns new arrays (the trend or a mask); nothing is changed in place, so the
interface can keep each step in the history and switch it off.

Biweight: the time-windowed Tukey biweight location (as Hippke et al. 2019 recommend for transit searches): at
each time the points within ± window / 2 are reduced to a location by iterating
w = (1 − u²)², u = (y − loc) / (c · MAD) (|u| < 1), loc = Σ w y / Σ w, from the median, c = 5.
"""

import numpy as np


def segments(t, gap_factor=5.0, gap=None):
    """Segment number of every point: a gap longer than gap_factor × the median cadence (or than gap, in the
    time unit) starts a new one."""
    t = np.asarray(t, float)
    dt = np.diff(t)
    limit = gap if gap is not None else gap_factor * np.median(dt)
    return np.concatenate([[0], np.cumsum(dt > limit)])


def event_mask(t, period, epoch, duration, factor=1.5):
    """True inside the events (eclipses, transits) of a known ephemeris, widened by factor."""
    phase = ((np.asarray(t, float) - epoch) / period + 0.5) % 1 - 0.5
    return np.abs(phase * period) < 0.5 * factor * duration


def _biweight(y, c=5.0, tol=1e-6, iterations=1000):
    """The scale (MAD about the median) stays fixed while the location iterates, to tol × MAD."""
    loc = np.median(y)
    mad = np.median(np.abs(y - loc))
    if mad == 0:
        return loc
    for _ in range(iterations):
        u = (y - loc) / (c * mad)
        w = np.where(np.abs(u) < 1, (1 - u * u) ** 2, 0.0)
        new = np.sum(w * y) / np.sum(w)
        if abs(new - loc) <= tol * mad:
            return new
        loc = new
    return loc


def _windowed(t, y, keep, window, reduce):
    out = np.full(len(t), np.nan)
    tk, yk = t[keep], y[keep]
    lo = np.searchsorted(tk, t - window / 2, "left")  # the window t − w/2 ≤ time < t + w/2
    hi = np.searchsorted(tk, t + window / 2, "left")
    for i, (a, b) in enumerate(zip(lo, hi, strict=True)):
        if b > a:
            out[i] = reduce(yk[a:b])
    return out


def trend(t, y, method="biweight", window=0.5, mask=None, gap_factor=5.0, gap=None, **options):
    """The trend at every point, computed per segment from the points outside mask. methods: "biweight",
    "median" (sliding, window in days), "savgol" (window in points, options order), "polynomial" (order by BIC up
    to options max_order, default 6), "spline" (knot spacing = window in days). gap: the segments' break in days
    (default gap_factor × the median cadence)."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    keep = np.isfinite(y) if mask is None else np.isfinite(y) & ~np.asarray(mask, bool)
    out = np.full(len(t), np.nan)
    seg = segments(t, gap_factor, gap)
    for s in np.unique(seg):
        sel = seg == s
        ts, ys, ks = t[sel], y[sel], keep[sel]
        if ks.sum() < 3:
            continue
        out[sel] = _one_segment(ts, ys, ks, method, window, options)
    return out


def _one_segment(t, y, keep, method, window, options):
    if method == "biweight":
        return _windowed(t, y, keep, window, lambda v: _biweight(v, options.get("c", 5.0)))
    if method == "median":
        return _windowed(t, y, keep, window, np.median)
    if method == "savgol":
        from scipy.signal import savgol_filter

        n = min(int(window) | 1, keep.sum() - (1 - keep.sum() % 2))
        smooth = savgol_filter(y[keep], n, options.get("order", 2))
        return np.interp(t, t[keep], smooth)
    if method == "polynomial":
        x = (t - t.mean()) / max(np.ptp(t), 1e-12)
        best = None
        for k in range(options.get("max_order", 6) + 1):
            c = np.polyfit(x[keep], y[keep], k)
            r = y[keep] - np.polyval(c, x[keep])
            n = keep.sum()
            bic = n * np.log(max(np.mean(r * r), 1e-300)) + (k + 1) * np.log(n)
            if best is None or bic < best[0]:
                best = (bic, c)
        return np.polyval(best[1], x)
    if method == "spline":
        from scipy.interpolate import LSQUnivariateSpline

        tk, yk = t[keep], y[keep]
        knots = np.arange(tk[0] + window, tk[-1] - window / 2, window)
        knots = knots[(np.searchsorted(tk, knots) > 3) & (np.searchsorted(tk, knots) < len(tk) - 3)]
        return LSQUnivariateSpline(tk, yk, knots, k=3)(t)
    raise ValueError(f"unknown detrending method: {method}")


def nightly_means(t, y, mask=None, gap_factor=5.0):
    """Each segment's (night's) mean of the points outside mask, at every point: subtract it to tie nights."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    keep = np.ones(len(t), bool) if mask is None else ~np.asarray(mask, bool)
    seg = segments(t, gap_factor)
    out = np.empty(len(t))
    for s in np.unique(seg):
        sel = seg == s
        out[sel] = np.mean(y[sel & keep]) if (sel & keep).any() else np.mean(y[sel])
    return out


def outliers(y, n_sigma=4.0, direction="both"):
    """True for points beyond n_sigma robust standard deviations of the median: "both", "up" (flares stay out of
    the mask's way: only upward points flagged when direction is "up"), or "down"."""
    y = np.asarray(y, float)
    med = np.nanmedian(y)
    sd = 1.4826 * np.nanmedian(np.abs(y - med))
    z = (y - med) / sd
    return {"both": np.abs(z) > n_sigma, "up": z > n_sigma, "down": z < -n_sigma}[direction]
