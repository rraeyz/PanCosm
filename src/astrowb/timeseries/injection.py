"""What could I have detected? (plans/period.md PER-12): signals of given periods and amplitudes injected into the
residuals (or any data), the chosen search run on each, the recovered fraction mapped; and the analytic 50 % level
of a sinusoid under the Lomb–Scargle search in white noise for comparison.

A signal counts as recovered when the search's best frequency is within `tolerance` (default half the frequency
resolution, 0.5 / span) of the injected one (or of its double / half when `aliases` is set, for eclipses).
"""

from concurrent.futures import ThreadPoolExecutor

import numpy as np


def sinusoid(t, period, amplitude, phase):
    return amplitude * np.sin(2 * np.pi * (t / period + phase))


def recovery(t, base, periods, amplitudes, search, n=20, signal=sinusoid, tolerance=None, aliases=False, seed=1,
             workers=4):  # fmt: skip
    """The recovered fraction on the grid (periods × amplitudes). search(t, y) → best period."""
    t, base = np.asarray(t, float), np.asarray(base, float)
    tol = 0.5 / np.ptp(t) if tolerance is None else tolerance
    rng = np.random.default_rng(seed)
    jobs = [(i, j, p, a, rng.uniform()) for i, p in enumerate(periods) for j, a in enumerate(amplitudes)
            for _ in range(n)]  # fmt: skip

    def one(job):
        i, j, p, a, ph = job
        best = search(t, base + signal(t, p, a, ph))
        ratios = [1.0, 0.5, 2.0] if aliases else [1.0]
        return i, j, any(abs(1 / best - 1 / (p * r)) < tol for r in ratios)

    hits = np.zeros((len(periods), len(amplitudes)))
    with ThreadPoolExecutor(workers) as pool:
        for i, j, ok in pool.map(one, jobs):
            hits[i, j] += ok
    return hits / n


def gls_half_amplitude(n_points, sigma, span, f_max):
    """The amplitude a sinusoid needs for its Lomb–Scargle peak to beat the highest noise peak half of the time:
    the noise maximum over M ≈ span · f_max independent frequencies has the median z with
    M (1 − z)^((N − 3)/2) = ln 2 (Scargle 1982 / Baluev 2008, the standard normalisation), and a sinusoid of
    amplitude A has the power z = (A²/2) / (σ² + A²/2), so A = σ √(2 z / (1 − z))."""
    m = span * f_max
    z = 1 - (np.log(2) / m) ** (2 / (n_points - 3))
    return float(sigma * np.sqrt(2 * z / (1 - z)))
