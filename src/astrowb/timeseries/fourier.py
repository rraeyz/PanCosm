"""Frequency analysis of pulsating and other periodic stars (what Period04 and Peranso do).

- Amplitude spectrum: Deeming (1975, Ap&SS 36, 137) discrete Fourier transform for uneven sampling,
  A(f) = 2/N |sum (y - <y>) exp(-2 pi i f t)|, in the units of y.
- Spectral window: the same transform of a constant; its side lobes show the aliases of the sampling.
- Multi-frequency fit y = c + sum A_k sin(2 pi (f_k t + phi_k)) by least squares (frequencies,
  amplitudes and phases all free), errors from Montgomery & O'Donoghue (1999, DSSN 13, 28).
- Prewhitening: the highest peak of the residual spectrum is added and every term refitted, until
  the peak's S/N (amplitude / mean residual amplitude around it) falls below 4 (Breger et al. 1993,
  A&A 271, 482).
- Times of maximum per cycle (parabola around each maximum of the fitted curve), phase binning,
  and light-curve editing helpers (sigma clipping, time binning, flux <-> magnitude).
"""

import numpy as np

_CHUNK = 2_000_000  # points x frequencies per block, keeps memory bounded


def _exp_sums(t, w, freqs):
    """S(f) = sum_n w_n exp(-2 pi i f t_n) for every f.
    On an evenly spaced grid exp(-2 pi i (f_b + j df) t) = exp(-2 pi i f_b t) exp(-2 pi i j df t): the second
    factor is the same for every block of frequencies, so it is computed once, and all blocks together are one
    matrix product. Both factors are evaluated directly (no recurrence), so the result equals the direct sum to
    rounding (tests/test_fourier.py); it is ~30 times faster than evaluating every cos / sin."""
    t, freqs = np.asarray(t, float), np.asarray(freqs, float)
    w = np.asarray(w, complex)
    out = np.empty(freqs.size, complex)
    rows = max(1, _CHUNK // max(1, t.size))
    d = np.diff(freqs)
    block = int(np.clip(rows, 8, 512))
    if freqs.size < 4 * block or not np.allclose(d, d[0], rtol=1e-9, atol=0):  # short or uneven grid: direct
        for i in range(0, freqs.size, rows):
            out[i : i + rows] = np.exp(-2j * np.pi * np.outer(freqs[i : i + rows], t)) @ w
        return out
    steps = np.exp(-2j * np.pi * np.outer(np.arange(block) * d[0], t))  # (block, N), shared by all blocks
    starts = np.arange(0, freqs.size, block)
    for c in range(0, starts.size, rows):  # columns in chunks: memory stays bounded for long series
        s = starts[c : c + rows]
        base = np.exp(-2j * np.pi * np.outer(t, freqs[s])) * w[:, None]  # (N, blocks)
        res = steps @ base  # res[j, b] = S(freqs[s_b] + j df)
        for b, i in enumerate(s):
            k = min(block, freqs.size - i)
            out[i : i + k] = res[:k, b]
    return out


def dft(t, y, freqs):
    """Deeming amplitude spectrum at the given frequencies (cycles per unit of t)."""
    t = np.asarray(t, float) - np.min(t)
    y = np.asarray(y, float) - np.mean(y)
    return 2 * np.abs(_exp_sums(t, y, freqs)) / t.size


def spectral_window(t, freqs):
    """Amplitude of the window function, 1 at f = 0."""
    t = np.asarray(t, float) - np.min(t)
    return np.abs(_exp_sums(t, np.ones_like(t), freqs)) / t.size


def default_grid(t, f_max, oversample=10):
    """0 .. f_max in steps of 1 / (oversample x time span)."""
    df = 1 / (oversample * np.ptp(t))
    return np.arange(df, f_max + df, df)


def _model(t, c, f, a, ph):
    return c + np.sum(a[:, None] * np.sin(2 * np.pi * (np.outer(f, t) + ph[:, None])), axis=0)


def fourier_fit(t, y, freqs):
    """Least-squares fit of len(freqs) sinusoids (starting from freqs). Returns a dict with arrays
    freq, amp, phase (cycles, 0..1) and their errors, the zero point, residual rms and t_ref
    (phases refer to t - t_ref)."""
    from scipy.optimize import least_squares

    t_abs, y = np.asarray(t, float), np.asarray(y, float)
    t_ref = float(np.min(t_abs))
    t = t_abs - t_ref
    f = np.atleast_1d(np.asarray(freqs, float))
    # linear start: amplitudes and phases for fixed frequencies
    cols = [np.ones_like(t)]
    for fk in f:
        cols += [np.sin(2 * np.pi * fk * t), np.cos(2 * np.pi * fk * t)]
    coef = np.linalg.lstsq(np.column_stack(cols), y, rcond=None)[0]
    s, c = coef[1::2], coef[2::2]
    a0, ph0 = np.hypot(s, c), np.arctan2(c, s) / (2 * np.pi)
    n = f.size

    def resid(p):
        return _model(t, p[0], p[1 : n + 1], p[n + 1 : 2 * n + 1], p[2 * n + 1 :]) - y

    p = least_squares(resid, np.concatenate([[coef[0]], f, a0, ph0]), x_scale="jac").x
    f, a, ph = p[1 : n + 1], p[n + 1 : 2 * n + 1], p[2 * n + 1 :]
    flip = a < 0
    a, ph = np.abs(a), (ph + 0.5 * flip) % 1.0
    sigma = float(np.std(resid(p), ddof=min(len(y) - 1, 3 * n + 1)))
    N, T = len(y), np.ptp(t)
    a_err = np.sqrt(2 / N) * sigma * np.ones(n)
    return {
        "freq": f,
        "freq_err": np.sqrt(6 / N) * sigma / (np.pi * T * a),
        "amp": a,
        "amp_err": a_err,
        "phase": ph,
        "phase_err": a_err / (2 * np.pi * a),
        "zero_point": float(p[0]),
        "rms": sigma,
        "t_ref": t_ref,
    }


def evaluate(fit, t):
    """The fitted curve at times t."""
    t = np.asarray(t, float) - fit["t_ref"]
    return _model(t, fit["zero_point"], np.asarray(fit["freq"]), np.asarray(fit["amp"]), np.asarray(fit["phase"]))


def noise_at(freqs, amp, f, box=2.0):
    """Mean amplitude of a residual spectrum within +-box/2 of f (Breger's noise)."""
    sel = np.abs(np.asarray(freqs) - f) <= box / 2
    return float(np.mean(np.asarray(amp)[sel])) if sel.any() else float(np.mean(amp))


def prewhiten(t, y, f_max, n_max=10, snr_min=4.0, oversample=10, box=2.0, progress=None):
    """Extract frequencies one by one. Returns (fit or None, freqs, spectrum of the data,
    spectrum of the final residuals, snr of each frequency)."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    grid = default_grid(t, f_max, oversample)
    first = dft(t, y, grid)
    found, fit, amp = [], None, first
    for k in range(n_max):
        if progress:
            progress(k / n_max)
        i = int(np.argmax(amp))
        fine = np.linspace(grid[max(i - 1, 0)], grid[min(i + 1, grid.size - 1)], 41)
        peak = float(fine[np.argmax(dft(t, y - (evaluate(fit, t) if fit else 0), fine))])
        trial = fourier_fit(t, y, [*found, peak])
        if np.any(np.diff(np.sort(trial["freq"])) < 1 / np.ptp(t)):  # unresolved: refit would merge terms
            break
        resid = dft(t, y - evaluate(trial, t), grid)
        # S/N against the spectrum after removing the peak (Breger 1993), so its own power is not "noise"
        if trial["amp"][-1] / noise_at(grid, resid, trial["freq"][-1], box) < snr_min:
            break
        fit, found, amp = trial, list(trial["freq"]), resid
    snr = [] if fit is None else [a / noise_at(grid, amp, f, box) for f, a in zip(fit["freq"], fit["amp"], strict=True)]
    return fit, grid, first, amp, np.asarray(snr)


def anova(t, y, p_min=0.05, p_max=None, n_harmonics=2, oversample=5):
    """Multi-harmonic analysis of variance (Schwarzenberg-Czerny 1996, ApJ 460, L107): F statistic
    of an n-harmonic Fourier series against a constant. Returns (periods, theta, best period)."""
    from astropy.timeseries import LombScargle

    from .period import _refine, frequency_grid

    t = np.asarray(t, float) - np.min(t)
    p_max = p_max or np.ptp(t) / 2
    ls = LombScargle(t, y, nterms=n_harmonics)
    dof = len(t) - 2 * n_harmonics - 1

    def theta(f, **kw):
        p = np.clip(ls.power(f, **kw), 0, 1 - 1e-12)
        return dof / (2 * n_harmonics) * p / (1 - p)

    freqs = frequency_grid(t, p_min, p_max, 1 / (oversample * n_harmonics))
    power = theta(freqs)
    return 1 / freqs, power, _refine(lambda f: theta(f, method="chi2"), freqs, power)


def bin_phase(phase, y, n_bins=50):
    """Mean and its error in equal phase bins on [-0.5, 0.5). Empty bins are left out."""
    phase, y = np.asarray(phase, float), np.asarray(y, float)
    k = np.clip(((phase + 0.5) * n_bins).astype(int), 0, n_bins - 1)
    n = np.bincount(k, minlength=n_bins)
    s, s2 = np.bincount(k, y, n_bins), np.bincount(k, y * y, n_bins)
    ok = n > 0
    mean = s[ok] / n[ok]
    var = np.where(n[ok] > 1, (s2[ok] - n[ok] * mean**2) / np.maximum(n[ok] - 1, 1), np.nan)
    centres = (np.arange(n_bins) + 0.5) / n_bins - 0.5
    return centres[ok], mean, np.sqrt(np.clip(var, 0, None) / n[ok]), n[ok]


def times_of_maximum(t, y, fit, window=0.15, min_points=7, magnitudes=False):
    """Time of each maximum covered by the data: parabola through the points within +-window
    periods of the fitted curve's maximum (main frequency). For magnitudes the maximum is the
    smallest value. Returns a list of (time, error)."""
    from .minima import polynomial_minimum

    t, y = np.asarray(t, float), np.asarray(y, float)
    period = 1 / fit["freq"][int(np.argmax(fit["amp"]))]
    grid = np.linspace(0, period, 400, endpoint=False) + t.min()
    m = evaluate(fit, grid)
    first = grid[np.argmin(m) if magnitudes else np.argmax(m)]
    out = []
    for k in range(int(np.floor((t.min() - first) / period)), int(np.ceil((t.max() - first) / period)) + 1):
        tc = first + k * period
        sel = np.abs(t - tc) <= window * period
        if sel.sum() < min_points or not (t[sel].min() < tc < t[sel].max()):
            continue
        try:
            tm, err = polynomial_minimum(t[sel], y[sel] if magnitudes else -y[sel])
        except (ValueError, np.linalg.LinAlgError):
            continue
        if abs(tm - tc) < window * period and np.isfinite(err):
            out.append((tm, err))
    return out


def _neighbour_median(y, wrap=False):
    """Median of the 3 values on either side of each point, without the point itself. A series' ends are extended
    point-symmetrically about the median of its first (last) three points, so a slope continues and an outlier at
    the very end is judged like any other point; a phase-folded curve wraps around."""
    from numpy.lib.stride_tricks import sliding_window_view

    if y.size < 7:
        return np.full(y.size, np.median(y))
    if wrap:
        padded = np.pad(y, 3, mode="wrap")
    else:
        lo, hi = np.median(y[:3]), np.median(y[-3:])
        padded = np.r_[2 * lo - y[5:2:-1], y, 2 * hi - y[-4:-7:-1]]
    return np.median(np.delete(sliding_window_view(padded, 7), 3, axis=1), axis=1)


def sigma_clip(y, n_sigma=4.0, t=None, period=None):
    """Mask of points kept: within n_sigma robust standard deviations of the median or, given the times, of the
    median of their neighbours in time (one night at a time), so that eclipses and pulsations stay as signal. With
    a period a point is also kept when it agrees with its neighbours in phase (sparse sharp eclipses), and a wrong
    period (half the true one) removes nothing that agrees in time."""
    y = np.asarray(y, float)
    if t is None:
        return _within(y - np.median(y), n_sigma)
    t = np.asarray(t, float)
    order = np.argsort(t)
    gaps = np.flatnonzero(np.diff(t[order]) > 10 * np.median(np.diff(t[order]))) + 1
    ref = np.empty_like(y)
    ref[order] = np.concatenate([_neighbour_median(p) for p in np.split(y[order], gaps)])
    keep = _within(y - ref, n_sigma)
    if period:
        order = np.argsort(t % period)
        ref[order] = _neighbour_median(y[order], wrap=True)
        keep |= _within(y - ref, n_sigma)
    return keep


def _within(d, n_sigma):
    d = d - np.median(d)
    mad = 1.4826 * np.median(np.abs(d))
    return np.abs(d) <= n_sigma * mad if mad > 0 else np.ones(d.size, bool)


def bin_time(t, y, width, err=None):
    """Means in consecutive time bins of the given width (empty bins left out). With err also returns the error of
    each mean: sqrt(sum σ²) / n (the points' own errors), or the scatter in the bin / √n if that is larger."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    k = np.floor((t - t.min()) / width).astype(int)
    _, idx, n = np.unique(k, return_inverse=True, return_counts=True)
    tb, yb = np.bincount(idx, t) / n, np.bincount(idx, y) / n
    if err is None:
        return tb, yb
    e = np.asarray(err, float)
    own = np.sqrt(np.bincount(idx, e**2)) / n
    spread = np.sqrt(np.maximum(np.bincount(idx, y**2) / n - yb**2, 0) / np.maximum(n - 1, 1))
    return tb, yb, np.where(n > 1, np.maximum(own, spread), own)


def _complex_dft(t, y, freqs):
    return _exp_sums(t, y, freqs) / t.size


def clean(t, y, f_max, oversample=10, gain=0.2, iterations=200, stop=1e-3):
    """CLEAN deconvolution of the amplitude spectrum (Roberts, Lehar & Dreher 1987, AJ 93, 968): the highest peak
    of the residual spectrum is taken as a component and its window pattern (all the aliases the sampling makes)
    is subtracted, `gain` of it at a time; the components, restored with a Gaussian beam the width of the
    window's main peak, plus the residuals give a spectrum without the aliases.
    Returns (frequencies >= 0, clean amplitude spectrum in the units of y, the list of (frequency, amplitude))."""
    t = np.asarray(t, float) - np.min(t)
    y = np.asarray(y, float) - np.mean(y)
    df = 1 / (oversample * np.ptp(t))
    n = int(np.ceil(f_max / df))
    nu = np.arange(-n, n + 1) * df  # dirty spectrum on -f_max .. f_max
    win_nu = np.arange(-2 * n, 2 * n + 1) * df  # window on twice the range, the same step
    dirty = _complex_dft(t, y, nu)
    window = _complex_dft(t, np.ones_like(t), win_nu)
    res = dirty.copy()
    comps = np.zeros(nu.size, complex)
    centre = 2 * n  # index of zero frequency in the window
    floor = stop * np.abs(dirty[n:]).max()
    for _ in range(iterations):
        j = n + int(np.argmax(np.abs(res[n:])))  # strongest positive frequency
        if np.abs(res[j]) < floor:
            break
        k = j - n  # its frequency index (>= 0)
        w2 = window[centre + 2 * k] if centre + 2 * k < window.size else 0.0
        a = (res[j] - np.conj(res[j]) * w2) / max(1 - abs(w2) ** 2, 1e-6)  # unbiased by its own negative image
        c = gain * a
        comps[j] += c
        comps[2 * n - j] += np.conj(c)
        idx = np.arange(nu.size)
        res -= c * window[centre + idx - j] + np.conj(c) * window[centre + idx - (2 * n - j)]
    # restoring beam: Gaussian with the half width of the window's main lobe
    main = np.abs(window[centre:])
    half = int(np.argmax(main < 0.5)) or 1
    sigma = half / np.sqrt(2 * np.log(2))
    kx = np.arange(-int(4 * sigma) - 1, int(4 * sigma) + 2)
    beam = np.exp(-0.5 * (kx / sigma) ** 2)
    restored = np.convolve(comps, beam, mode="same") + res
    found = [(float(nu[j]), float(2 * abs(comps[j]))) for j in range(n, nu.size) if abs(comps[j]) > 0]
    found.sort(key=lambda fa: -fa[1])
    return nu[n:], 2 * np.abs(restored[n:]), found
