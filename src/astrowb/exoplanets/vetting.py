"""The vetting sheet's numbers (plans/exoplanets.md EXO-11), after Thompson et al. 2018 and Twicken et al. 2018:
odd against even transit depths, a secondary eclipse at phase 0.5, a sinusoid at the period out of transit
(ellipsoidal variation or heating, the "SWEET" test), and a V-shape. Each test gives a mark — "green", "amber" or
"red" — and its number; together they are a diagnosis aid, never a verdict."""

import numpy as np


def _phase(t, period, t0):
    return ((np.asarray(t, float) - t0) / period + 0.5) % 1.0 - 0.5


def _depth(f, err, inside, outside):
    w_in, w_out = 1 / err[inside] ** 2, 1 / err[outside] ** 2
    m_in, m_out = np.sum(w_in * f[inside]) / np.sum(w_in), np.sum(w_out * f[outside]) / np.sum(w_out)
    return m_out - m_in, float(np.sqrt(1 / np.sum(w_in) + 1 / np.sum(w_out)))


def _mark(sigma, amber=2.0, red=3.0):
    return "red" if sigma >= red else "amber" if sigma >= amber else "green"


def odd_even(t, f, err, period, t0, duration):
    """The depths of odd and even transits and their difference in σ (an eclipsing binary at twice the period)."""
    t, f, err = (np.asarray(v, float) for v in (t, f, err))
    n = np.round((t - t0) / period)
    ph = _phase(t, period, t0) * period
    inside = np.abs(ph) < 0.25 * duration
    outside = np.abs(ph) > 0.75 * duration
    odd, even = n % 2 == 1, n % 2 == 0
    d_odd, e_odd = _depth(f, err, inside & odd, outside)
    d_even, e_even = _depth(f, err, inside & even, outside)
    sigma = abs(d_odd - d_even) / np.hypot(e_odd, e_even)
    return {"odd": d_odd, "even": d_even, "sigma": float(sigma), "mark": _mark(sigma)}


def secondary(t, f, err, period, t0, duration, phase=0.5):
    """The depth at the given phase (0.5 for a circular orbit) and its significance."""
    t, f, err = (np.asarray(v, float) for v in (t, f, err))
    ph = ((t - t0) / period - phase + 0.5) % 1.0 - 0.5
    inside = np.abs(ph * period) < 0.25 * duration
    outside = (np.abs(ph * period) > 0.75 * duration) & (np.abs(_phase(t, period, t0) * period) > 0.75 * duration)
    d, e = _depth(f, err, inside, outside)
    return {"depth": d, "error": e, "sigma": float(d / e), "mark": _mark(d / e)}


def sweet(t, f, err, period, t0, duration):
    """Sinusoids at P, P/2 and 2P fitted out of transit: the largest amplitude in σ (ellipsoidal at P/2)."""
    t, f, err = (np.asarray(v, float) for v in (t, f, err))
    keep = np.abs(_phase(t, period, t0) * period) > 0.75 * duration
    best = 0.0
    for p in (period, period / 2, 2 * period):
        x = 2 * np.pi * (t[keep] - t0) / p
        a = np.column_stack([np.ones_like(x), np.sin(x), np.cos(x)]) / err[keep, None]
        coef, *_ = np.linalg.lstsq(a, f[keep] / err[keep], rcond=None)
        cov = np.linalg.inv(a.T @ a)
        amp = np.hypot(coef[1], coef[2])
        best = max(best, amp / np.sqrt(0.5 * (cov[1, 1] + cov[2, 2])))
    return {"sigma": float(best), "mark": _mark(best)}


def v_shape(b, k):
    """b + k above 1: a grazing, V-shaped event, more often an eclipsing binary (amber), above 1.2 red."""
    s = b + k
    return {"value": float(s), "mark": "red" if s > 1.2 else "amber" if s > 1.0 else "green"}


def sheet(t, f, err, period, t0, duration, b=None, k=None):
    args = (t, f, err, period, t0, duration)
    out = {"odd_even": odd_even(*args), "secondary": secondary(*args), "sweet": sweet(*args)}
    if b is not None and k is not None:
        out["v_shape"] = v_shape(b, k)
    return out
