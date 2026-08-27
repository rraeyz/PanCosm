"""Period search: Lomb-Scargle (sinusoids, pulsators), BLS (transits, Algol-type eclipses) and
phase dispersion minimisation (any light-curve shape, Stellingwerf 1978, ApJ 224, 953).

Lomb-Scargle and BLS come from astropy.timeseries; PDM is implemented here from the paper.
Every function returns (periods, power) with "higher is better" (PDM returns 1 - theta) and
the best period.
"""

import numpy as np
from astropy.timeseries import BoxLeastSquares, LombScargle


def frequency_grid(t, p_min, p_max, phase_resolution):
    """Ascending frequencies whose step shifts the phase by at most phase_resolution over the data span."""
    df = phase_resolution / np.ptp(t)
    return np.arange(1 / p_max, 1 / p_min + df, df)


def search(t, p_min, p_max, res, power, budget, peaks=8):
    """(freqs, power, best frequency) over p_min..p_max, frequency step res / span (res: phase step over the
    span); t sorted; power(idx, freqs) scores the points t[idx] on trial frequencies.

    Years of data (several TESS sectors or seasons) need millions of trial frequencies, times every point: hours.
    When frequencies x points exceed the budget, the densest stretch of the data that fits is searched first (a
    shorter span needs fewer frequencies), then all the data around its best peaks (+-2 coarse steps on the full
    grid), which decides the cycle count across the gaps. The returned periodogram is then the coarse one."""
    f_lo, f_hi, span, n = 1 / p_max, 1 / p_min, np.ptp(t), len(t)

    def cost(w, m):
        return (f_hi - f_lo) * w / res * m

    if cost(span, n) <= budget:
        freqs = frequency_grid(t, p_min, p_max, res)
        pw = power(np.arange(n), freqs)
        return freqs, pw, freqs[int(np.argmax(pw))]
    shortest = min(span, 2 * p_max)  # two cycles of the longest period must fit
    w = span
    while True:
        w = max(w / 2, shortest)
        end = np.searchsorted(t, t + w, side="right")
        i = int(np.argmax(end - np.arange(n)))
        sel = np.arange(i, end[i])
        if cost(w, len(sel)) <= budget or w <= shortest:
            break
    sel = sel[:: int(np.ceil(cost(w, len(sel)) / budget))]  # still too much: every k-th point of the stretch
    freqs = frequency_grid(t[sel], p_min, p_max, res)
    pw = power(sel, freqs)
    df = freqs[1] - freqs[0]
    local = np.flatnonzero((pw[1:-1] >= pw[:-2]) & (pw[1:-1] >= pw[2:])) + 1
    best_f, best_p = freqs[int(np.argmax(pw))], -np.inf
    for k in local[np.argsort(pw[local])[::-1][:peaks]]:
        fine = np.arange(freqs[k] - 2 * df, freqs[k] + 2 * df, res / span)
        fp = power(np.arange(n), fine[fine > 0])
        if fp.max() > best_p:
            best_p, best_f = fp.max(), fine[fine > 0][int(np.argmax(fp))]
    return freqs, pw, best_f


def _refine(score, freqs, power):
    """Best frequency refined on a 50x finer grid around the coarse peak."""
    i = int(np.argmax(power))
    df = freqs[1] - freqs[0]
    fine = np.linspace(freqs[i] - df, freqs[i] + df, 101)
    fine = fine[fine > 0]
    return float(1 / fine[np.argmax(score(fine))])


def lomb_scargle(t, y, err=None, p_min=0.05, p_max=None, oversample=5):
    t = np.asarray(t, float) - np.min(t)  # small numbers keep the phases exact
    p_max = p_max or np.ptp(t) / 2
    ls = LombScargle(t, y, err)
    freqs = frequency_grid(t, p_min, p_max, 1 / oversample)
    power = ls.power(freqs)
    return 1 / freqs, power, _refine(lambda f: ls.power(f, method="slow"), freqs, power)


def bls(t, y, err=None, p_min=0.2, p_max=None, durations=(0.04, 0.06, 0.08, 0.12, 0.16), budget=2e9):
    order = np.argsort(t)
    t = np.asarray(t, float)[order] - np.min(t)
    y = np.asarray(y, float)[order]
    e = None if err is None else np.asarray(err, float)[order]
    p_max = p_max or np.ptp(t) / 2
    p_min = max(p_min, 2 * max(durations))

    def power(idx, f):
        model = BoxLeastSquares(t[idx], y[idx], None if e is None else e[idx])
        return np.asarray(model.power(1 / f, durations).power)

    # frequency step as astropy's autoperiod at p_max = span / 2: a box moves by less than its duration
    freqs, pw, best = search(t, p_min, p_max, 0.5 * min(durations) / p_max, power, budget)
    return 1 / freqs, pw, float(1 / best)


def _pdm_power(t, y, periods, n_bins):
    from ..compute.periods import gpu_pdm_power

    gpu = gpu_pdm_power(t, y, 1 / np.asarray(periods, float), n_bins)  # when the compute mode allows it
    if gpu is not None:
        return gpu
    total = np.var(y, ddof=1)
    out = np.empty(len(periods))
    for i, p in enumerate(periods):
        bins = np.floor((t / p % 1.0) * n_bins).astype(int)
        n = np.bincount(bins, minlength=n_bins)
        s = np.bincount(bins, y, n_bins)
        s2 = np.bincount(bins, y * y, n_bins)
        ok = n > 1
        within = (s2[ok] - s[ok] ** 2 / n[ok]).sum() / (n[ok].sum() - ok.sum())
        out[i] = 1 - within / total
    return out


def pdm(t, y, p_min=0.05, p_max=None, n_bins=20, oversample=3, budget=2e8):
    """theta = pooled variance in phase bins / total variance; returns power = 1 - theta."""
    order = np.argsort(t)
    t, y = np.asarray(t, float)[order] - np.min(t), np.asarray(y, float)[order]
    p_max = p_max or np.ptp(t) / 2
    res = 1 / (n_bins * oversample)
    freqs, power, best = search(t, p_min, p_max, res, lambda i, f: _pdm_power(t[i], y[i], 1 / f, n_bins), budget)
    step = res / np.ptp(t)
    return 1 / freqs, power, _refine(lambda f: _pdm_power(t, y, 1 / f, n_bins), np.array([best - step, best]), [0, 1])


def fold(t, period, t0=0.0):
    """Phase in [-0.5, 0.5) with phase 0 at t0."""
    return ((np.asarray(t, float) - t0) / period + 0.5) % 1.0 - 0.5
