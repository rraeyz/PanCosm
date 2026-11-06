"""Broadening function (BF): the Doppler broadening kernel that turns a sharp-lined template into the
observed spectrum, found by linear least squares (Rucinski 1992, AJ 104, 1968; 2002, AJ 124, 1746).

Unlike a cross-correlation, the BF does not mix the line profile with the template's own lines: each
star of a binary shows up as its own rotational profile, with its velocity, v sin i and light share.
That makes it the method of choice for fast rotators and contact (W UMa) binaries, where CCF and TODCOR
peaks are broad and blend. Own implementation from the papers.
"""

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares
from scipy.signal import find_peaks

from .rv import C_KMS, v_from_ln


def rotational_profile(v, v0, vsini, eps=0.6):
    """Gray's rotational broadening profile with linear limb darkening eps, unit area (per km/s)."""
    x = (np.asarray(v, float) - v0) / vsini
    inside = np.abs(x) < 1
    y = np.zeros_like(x)
    r = 1 - x[inside] ** 2
    y[inside] = (2 * (1 - eps) * np.sqrt(r) + 0.5 * np.pi * eps * r) / (np.pi * vsini * (1 - eps / 3))
    return y


def broadening_function(
    wave, flux, t_wave, t_flux, v_min=-400.0, v_max=400.0, v_step=None, smooth=1.5, components=1, eps=0.6
):
    """BF of a continuum-normalised spectrum against a sharp-lined template, and a fit of `components`
    rotational profiles. smooth: Gaussian smoothing in velocity bins (BF noise grows with resolution).
    Returns dict(v, bf, bf_smooth, model, components=[{rv, rv_err, vsini, vsini_err, strength}],
    strongest component first)."""
    wave, flux, t_wave, t_flux = (np.asarray(a, float) for a in (wave, flux, t_wave, t_flux))
    if v_step is None:  # the observed sampling; finer only adds noise
        v_step = C_KMS * np.median(np.diff(np.log(wave)))
    dln = v_step / C_KMS
    lags = np.arange(int(np.floor(v_min / v_step)), int(np.ceil(v_max / v_step)) + 1)
    ln_w, ln_t = np.log(wave), np.log(t_wave)
    lo = max(ln_w[0], ln_t[0] + lags.max() * dln)
    hi = min(ln_w[-1], ln_t[-1] + lags.min() * dln)
    grid = np.arange(lo, hi, dln)
    if len(grid) < 3 * len(lags):
        raise ValueError("observed and template spectra hardly overlap for this velocity range")
    # program = sum over velocities of the shifted template's line depths, weighted by the BF
    program = 1.0 - np.interp(grid, ln_w, flux)
    design = np.column_stack([1.0 - np.interp(grid - k * dln, ln_t, t_flux) for k in lags])
    bf = np.linalg.lstsq(design, program, rcond=1e-3)[0] / v_step  # per km/s, so areas are light shares
    v = v_from_ln(lags * dln)
    bfs = gaussian_filter1d(bf, smooth) if smooth else bf
    comps, model = _fit(v, bfs, components, eps, v_step, smooth)
    return {"v": v.tolist(), "bf": bf.tolist(), "bf_smooth": bfs.tolist(), "model": model.tolist(), "components": comps}


def _least_squares(v, bf, start, eps, v_step, smooth=0.0):
    n = (len(start) - 1) // 3

    def model(x):  # smoothed as the BF it is fitted to: a sharp star's profile otherwise leaves wings
        m = x[0] + sum(x[1 + 3 * i] * rotational_profile(v, x[2 + 3 * i], x[3 + 3 * i], eps) for i in range(n))
        return gaussian_filter1d(m, smooth) if smooth else m

    lower = [-np.inf] + [0, v[0], v_step] * n
    upper = [np.inf] + [np.inf, v[-1], v[-1] - v[0]] * n
    return least_squares(lambda x: model(x) - bf, start, bounds=(lower, upper)), model


def _start(v, bf, p, v_step, n=1):
    width = np.sum(bf > bf[p] / 2) * v_step / n
    return [bf[p] * width, v[p], max(width, 3 * v_step)]  # area, centre, v sin i


def _fit(v, bf, n, eps, v_step, smooth=0.0):
    rough = gaussian_filter1d(bf, max(1.0, 10 / v_step))  # noise ripples on a broad profile are not stars
    peaks, _ = find_peaks(rough, prominence=0.1 * rough.max(), distance=max(1, int(20 / v_step)))
    peaks = sorted(peaks[np.argsort(rough[peaks])[::-1][:n]])
    start = [0.0] + [s for p in peaks for s in _start(v, bf, p, v_step, n)]
    # a fast rotator's broad, low profile on the shoulder of a sharp one makes no peak of its own (TZ For: v sin i
    # 46 against 6 km/s, 14 of 22 HARPS spectra): as Rucinski does, fit what is there, then look for the next star
    # in what is left of the BF, and fit them together
    while (len(start) - 1) // 3 < n:
        if len(start) == 1:
            raise ValueError(f"the broadening function shows fewer than {n} peaks")
        sol, model = _least_squares(v, bf, start, eps, v_step, smooth)
        left = gaussian_filter1d(bf - model(sol.x), max(1.0, 10 / v_step))
        # the found stars' own profiles are left out: a model never fits them exactly, and what it misses is no star
        away = np.ones(len(v), bool)
        for i in range((len(sol.x) - 1) // 3):
            away &= np.abs(v - sol.x[2 + 3 * i]) > sol.x[3 + 3 * i] + max(10.0, 3 * v_step)
        if away.sum() < 10:
            raise ValueError(f"the broadening function shows fewer than {n} peaks")
        noise = 1.4826 * np.median(np.abs(left[away] - np.median(left[away]))) + 1e-12
        p = int(np.flatnonzero(away)[np.argmax(left[away])])
        if left[p] < 5 * noise:
            raise ValueError(f"the broadening function shows fewer than {n} peaks")
        fwhm = np.sum(left > left[p] / 2) * v_step
        # area, centre, v sin i (about 0.55 FWHM for a rotational profile)
        start = list(sol.x) + [left[p] * fwhm, v[p], max(0.55 * fwhm, 3 * v_step)]
    sol, model = _least_squares(v, bf, start, eps, v_step, smooth)
    resid = sol.fun
    dof = max(len(v) - len(start), 1)
    try:
        cov = np.linalg.inv(sol.jac.T @ sol.jac) * np.sum(resid**2) / dof
        err = np.sqrt(np.clip(np.diag(cov), 0, None))
    except np.linalg.LinAlgError:
        err = np.full(len(start), np.nan)
    comps = [
        {
            "rv": float(sol.x[2 + 3 * i]),
            "rv_err": float(err[2 + 3 * i]),
            "vsini": float(sol.x[3 + 3 * i]),
            "vsini_err": float(err[3 + 3 * i]),
            "strength": float(sol.x[1 + 3 * i]),
        }
        for i in range(n)
    ]
    comps.sort(key=lambda c: -c["strength"])
    return comps, model(sol.x)
