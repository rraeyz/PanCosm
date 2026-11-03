"""Rotation and flares (plans/period.md PER-15).

Rotation by the autocorrelation function (McQuillan, Aigrain & Mazeh 2013, MNRAS 432, 1203): the curve on a
regular grid (gaps as zeros after the mean), its ACF smoothed by a Gaussian of 56 % of the grid… scaled to the
lag, the first local maximum taken, and refined as the median spacing of the first peaks (several rotations
together: robust against a stronger half-period peak).

Flares: after a running median removes the rotation, a run of at least `n_points` consecutive points above
`n_sigma` robust σ; each flare's start, peak, end and equivalent duration ∫ (F / F_quiet − 1) dt.
"""

import numpy as np


def acf(t, y, step=None):
    """(lags, ACF) on a regular grid of the data's median cadence."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    step = step or np.median(np.diff(np.sort(t)))
    grid = np.arange(t.min(), t.max() + step, step)
    filled = np.zeros(grid.size)
    idx = np.clip(np.round((t - t.min()) / step).astype(int), 0, grid.size - 1)
    filled[idx] = y - np.mean(y)
    mask = np.zeros(grid.size)
    mask[idx] = 1
    n = 1 << int(np.ceil(np.log2(2 * grid.size)))
    num = np.fft.irfft(np.abs(np.fft.rfft(filled, n)) ** 2, n)[: grid.size]
    den = np.fft.irfft(np.abs(np.fft.rfft(mask, n)) ** 2, n)[: grid.size]
    out = np.where(den > 0.25 * den[0], num / np.maximum(den, 1e-12), 0.0)
    return np.arange(grid.size) * step, out / out[0]


def acf_period(t, y, max_lag=None):
    """The rotation period from the ACF's peaks (None when it shows none)."""
    from scipy.ndimage import gaussian_filter1d
    from scipy.signal import find_peaks

    lags, r = acf(t, y)
    if max_lag:
        keep = lags <= max_lag
        lags, r = lags[keep], r[keep]
    smooth = gaussian_filter1d(r, max(len(r) / 200, 1.0))
    peaks, props = find_peaks(smooth, prominence=0.05)
    if not len(peaks):
        return None
    first = lags[peaks[0]]
    # a stronger second peak at about twice the first: the first was a half-period (two spots)
    if len(peaks) > 1 and abs(lags[peaks[1]] / first - 2) < 0.2 and smooth[peaks[1]] > 1.2 * smooth[peaks[0]]:
        first = lags[peaks[1]]
    ratio = lags[peaks[:6]] / first
    near = (np.round(ratio) >= 1) & (np.abs(ratio - np.round(ratio)) < 0.15)  # the rotation's own multiples only
    multiples = lags[peaks[:6]][near] / np.round(ratio[near])
    return float(np.median(multiples))


def flares(t, y, n_sigma=3.0, n_points=3, window=None):
    """[{"start", "peak", "end", "amplitude", "ed"}] (ed: equivalent duration in the time unit)."""
    from .clean import trend

    t, y = np.asarray(t, float), np.asarray(y, float)
    window = window or 20 * np.median(np.diff(t)) * 3
    quiet = trend(t, y, "median", window)
    rel = y / quiet - 1
    sd = 1.4826 * np.median(np.abs(rel - np.median(rel)))
    above = rel > n_sigma * sd
    out, i = [], 0
    while i < len(t):
        if not above[i]:
            i += 1
            continue
        j = i
        while j < len(t) and above[j]:
            j += 1
        if j - i >= n_points:
            a, b = max(i - 1, 0), min(j, len(t) - 1)
            seg = slice(a, b + 1)
            k = a + int(np.argmax(rel[seg]))
            out.append({"start": t[a], "peak": t[k], "end": t[b], "amplitude": float(rel[k]),
                        "ed": float(np.trapezoid(rel[seg], t[seg]))})  # fmt: skip
        i = j
    return out
