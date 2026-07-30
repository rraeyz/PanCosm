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


def bls(t, y, err=None, p_min=0.2, p_max=None, durations=(0.04, 0.06, 0.08, 0.12, 0.16)):
    t = np.asarray(t, float) - np.min(t)
    p_max = p_max or np.ptp(t) / 2
    model = BoxLeastSquares(t, y, err)
    periods = model.autoperiod(durations, minimum_period=max(p_min, 2 * max(durations)), maximum_period=p_max)
    result = model.power(periods, durations)
    return np.asarray(periods), np.asarray(result.power), float(periods[np.argmax(result.power)])


def _pdm_power(t, y, periods, n_bins):
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


def pdm(t, y, p_min=0.05, p_max=None, n_bins=20, oversample=3):
    """theta = pooled variance in phase bins / total variance; returns power = 1 - theta."""
    t, y = np.asarray(t, float) - np.min(t), np.asarray(y, float)
    p_max = p_max or np.ptp(t) / 2
    freqs = frequency_grid(t, p_min, p_max, 1 / (n_bins * oversample))
    power = _pdm_power(t, y, 1 / freqs, n_bins)
    return 1 / freqs, power, _refine(lambda f: _pdm_power(t, y, 1 / f, n_bins), freqs, power)


def fold(t, period, t0=0.0):
    """Phase in [-0.5, 0.5) with phase 0 at t0."""
    return ((np.asarray(t, float) - t0) / period + 0.5) % 1.0 - 0.5
