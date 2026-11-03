"""Asteroid rotation, the FALC way (Harris et al. 1989, Icarus 77, 171) (plans/period.md PER-11): at each trial
period a Fourier series of order m in the rotational phase and a free zero point per night are fitted by linear
least squares; the period spectrum is the RMS of the residuals against the period. The series order is chosen by an
F-test; asteroids usually show two maxima per rotation, so the double-peaked solution (twice the strongest
single-harmonic period) is the one reported, as is usual."""

import numpy as np
from scipy import stats


def _design(t, nights, period, order):
    names, idx = np.unique(nights, return_inverse=True)
    cols = [(idx == k).astype(float) for k in range(len(names))]
    ph = 2 * np.pi * t / period
    for k in range(1, order + 1):
        cols += [np.sin(k * ph), np.cos(k * ph)]
    return np.column_stack(cols), len(names)


def fit(t, mag, err, nights, period, order):
    """(rms, χ², number of parameters, coefficients, number of nights)."""
    a, n_nights = _design(np.asarray(t, float), np.asarray(nights), period, order)
    w = 1 / np.asarray(err, float)
    coef, *_ = np.linalg.lstsq(a * w[:, None], np.asarray(mag, float) * w, rcond=None)
    r = np.asarray(mag, float) - a @ coef
    return float(np.sqrt(np.mean(r * r))), float(np.sum((r * w) ** 2)), a.shape[1], coef, n_nights


def spectrum(t, mag, err, nights, periods, order=4):
    return np.array([fit(t, mag, err, nights, p, order)[0] for p in periods])


def best_order(t, mag, err, nights, period, max_order=8, alpha=0.01):
    """The highest order whose harmonic is significant by the F-test against the order below (a missing harmonic,
    say the third of a double-peaked curve, does not stop the search)."""
    order = 1
    for m in range(2, max_order + 1):
        _r0, c0, k0, _c, _n = fit(t, mag, err, nights, period, m - 1)
        _r1, c1, k1, _c, _n = fit(t, mag, err, nights, period, m)
        dof = len(t) - k1
        f = ((c0 - c1) / (k1 - k0)) / (c1 / dof)
        if stats.f.sf(f, k1 - k0, dof) <= alpha:
            order = m
    return order


def amplitude(coef, n_nights, order, n=2000):
    """Peak-to-peak amplitude of the composite curve (zero points removed)."""
    ph = 2 * np.pi * np.arange(n) / n
    y = sum(coef[n_nights + 2 * (k - 1)] * np.sin(k * ph) + coef[n_nights + 2 * k - 1] * np.cos(k * ph)
            for k in range(1, order + 1))  # fmt: skip
    return float(np.ptp(y))


def search(t, mag, err, nights, p_min, p_max, order=4, n=5000):
    """(periods, rms, best period): the lowest RMS of the spectrum, refined on a fine grid around it."""
    periods = np.geomspace(p_min, p_max, n)
    rms = spectrum(t, mag, err, nights, periods, order)
    k = int(np.argmin(rms))
    fine = np.linspace(periods[max(k - 2, 0)], periods[min(k + 2, n - 1)], 200)
    return periods, rms, float(fine[int(np.argmin(spectrum(t, mag, err, nights, fine, order)))])
