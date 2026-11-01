"""Period-search methods beyond period.py's (plans/period.md PER-3), each from its paper, each returning
(periods, power, best period) with higher power better, like period.lomb_scargle:

- gls: the generalised Lomb–Scargle with a floating mean, weights and n harmonics (Zechmeister & Kürster 2009,
  A&A 496, 577; VanderPlas & Ivezić 2015 for the harmonics) — Astropy's implementation;
- aovmh: multi-harmonic analysis of variance (Schwarzenberg-Czerny 1996, ApJ 460, L107): a Fourier series of n
  harmonics fitted at every frequency, Θ = (N − 2n − 1) · S_model / (2n · S_residual) — for any smooth shape
  (pulsators, eclipsing binaries);
- conditional_entropy: Graham et al. 2013 (MNRAS 434, 2629): the entropy of the magnitudes given the phase in a
  10 × 5 grid of the unit square, lower when the folded curve is thin; power = 1 − H / ln 5 — sparse survey data;
- string_length: Lafler & Kinman 1965: the sum of squared differences of neighbours in phase over the total
  variance (about 2 for no period), power = 1 − Θ / 2 — sharp eclipses, few points; two cycles folded on top of
  each other score the same, so the shortest of k · P within 3 % of the best is taken.
"""

import numpy as np

from .period import _refine, search


def _prepare(t, y, err=None):
    order = np.argsort(t)
    t = np.asarray(t, float)[order]
    y = np.asarray(y, float)[order]
    w = np.ones_like(y) if err is None else 1 / np.asarray(err, float)[order] ** 2
    return t - t[0], y, w


def gls(t, y, err=None, p_min=0.05, p_max=None, nterms=1, oversample=5):
    from astropy.timeseries import LombScargle

    from .period import frequency_grid

    order = np.argsort(t)
    t = np.asarray(t, float)[order]
    t = t - t[0]
    e = None if err is None else np.asarray(err, float)[order]
    p_max = p_max or np.ptp(t) / 2
    ls = LombScargle(t, np.asarray(y, float)[order], e, nterms=nterms)
    freqs = frequency_grid(t, p_min, p_max, 1 / oversample / max(1, nterms))
    power = ls.power(freqs)
    return 1 / freqs, power, _refine(ls.power, freqs, power)


def _aovmh_power(t, y, w, freqs, n):
    out = np.empty(len(freqs))
    sw = np.sqrt(w)
    ym = np.sum(w * y) / np.sum(w)
    total = np.sum(w * (y - ym) ** 2)
    k = np.arange(1, n + 1)
    dof_model, dof_resid = 2 * n, len(y) - 2 * n - 1
    for i, f in enumerate(freqs):
        arg = 2 * np.pi * f * t[:, None] * k
        a = np.column_stack([np.ones_like(t), np.cos(arg), np.sin(arg)]) * sw[:, None]
        coef, *_ = np.linalg.lstsq(a, y * sw, rcond=None)
        resid = np.sum((a @ coef - y * sw) ** 2)
        out[i] = (dof_resid * (total - resid)) / (dof_model * max(resid, 1e-300))
    return out


def aovmh(t, y, err=None, p_min=0.05, p_max=None, n_harmonics=8, oversample=5, budget=2e8):
    """n harmonics resolve eclipses as narrow as about 1 / (2n) of the cycle; k times the period fits as well as
    the period itself whenever its harmonics cover the shape — with gaps its spare harmonics fit some noise and it
    scored up to 9 % higher (sine, nightly data) — so the shortest period whose Θ is at least 0.8 of the best is
    taken (a true half period scored 0.01–0.1 of the period's own on sine, saw-tooth and Algol curves)."""
    t, y, w = _prepare(t, y, err)
    p_max = p_max or np.ptp(t) / 2

    def score(f):
        return _aovmh_power(t, y, w, f, n_harmonics)

    res = 1 / (oversample * n_harmonics)
    freqs, power, best = search(t, p_min, p_max, res,
                                lambda i, f: _aovmh_power(t[i], y[i], w[i], f, n_harmonics), budget)  # fmt: skip
    step = res / np.ptp(t)
    best_f = 1 / _fine(score, best, step)
    return 1 / freqs, power, float(1 / _shortest(score, best_f, step, 1 / p_min, n_harmonics, 0.8))


def _ce_power(t, y, freqs, n_phase=10, n_mag=5):
    m = (y - y.min()) / max(np.ptp(y), 1e-300)
    mbin = np.minimum((m * n_mag).astype(int), n_mag - 1)
    out = np.empty(len(freqs))
    for i, f in enumerate(freqs):
        pbin = np.minimum(((t * f) % 1.0 * n_phase).astype(int), n_phase - 1)
        joint = np.bincount(pbin * n_mag + mbin, minlength=n_phase * n_mag).reshape(n_phase, n_mag) / len(t)
        phase = joint.sum(axis=1, keepdims=True)
        ok = joint > 0
        h = np.sum(joint[ok] * np.log(np.broadcast_to(phase, joint.shape)[ok] / joint[ok]))
        out[i] = 1 - h / np.log(n_mag)
    return out


def conditional_entropy(t, y, err=None, p_min=0.05, p_max=None, oversample=3, budget=2e8):
    t, y, _w = _prepare(t, y, err)
    p_max = p_max or np.ptp(t) / 2
    res = 1 / (10 * oversample)
    freqs, power, best = search(t, p_min, p_max, res, lambda i, f: _ce_power(t[i], y[i], f), budget)
    return 1 / freqs, power, _fine(lambda f: _ce_power(t, y, f), best, res / np.ptp(t))


def _sl_power(t, y, freqs):
    total = np.sum((y - y.mean()) ** 2)
    out = np.empty(len(freqs))
    for i, f in enumerate(freqs):
        order = np.argsort((t * f) % 1.0)
        ys = y[order]
        out[i] = 1 - (np.sum(np.diff(ys) ** 2) + (ys[0] - ys[-1]) ** 2) / (2 * total)
    return out


def string_length(t, y, err=None, p_min=0.05, p_max=None, oversample=3, budget=2e8):
    t, y, _w = _prepare(t, y, err)
    p_max = p_max or np.ptp(t) / 2
    res = 1 / (len(t) ** 0.5 * oversample)  # the curve is resolved to about √N points per cycle
    freqs, power, best = search(t, p_min, p_max, res, lambda i, f: _sl_power(t[i], y[i], f), budget)

    def score(f):
        return _sl_power(t, y, f)

    step = res / np.ptp(t)
    best_f = 1 / _fine(score, best, step)
    return 1 / freqs, power, float(1 / _shortest(score, best_f, step, 1 / p_min, 4, 0.97))


def _shortest(score, best_f, step, f_max, k_max, ratio):
    """A fold statistic scores k times the period about as well as the period (the cycles lie on top of each
    other): the highest k ≤ k_max whose k · best_f scores at least `ratio` of best_f's, as a frequency."""
    top = score(np.array([best_f]))[0]
    for k in range(k_max, 1, -1):
        f = k * best_f
        if f <= f_max:  # the error of best_f grows k times at k · best_f
            fine = np.linspace(f - k * step, f + k * step, 20 * k + 1)
            got = score(fine)
            if got.max() >= ratio * top:
                return 1 / _fine(score, fine[int(np.argmax(got))], step)
    return best_f


def _fine(score, best, step):
    fine = np.linspace(best - step, best + step, 41)
    fine = fine[fine > 0]
    return float(1 / fine[int(np.argmax(score(fine)))])
