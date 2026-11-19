"""Is the catalogue ephemeris still good? The O−C of the newest minima against it (plans/oc.md OC-14)."""

import time

import numpy as np

from .ephemeris import Minimum, epochs

MIN_PER_DAY = 1440.0


def against(minima_times, errors, t0, period, newest=10, kinds=None, now_jd=None, tolerance_min=5.0):
    """O−C of the newest `newest` minima against the catalogue ephemeris (t0, period), as a JSON-serialisable dict.

    `kinds` gives "I" or "II" per minimum (secondaries sit at half cycles, as in ephemeris.epochs). `errors` are
    in days; when any is missing the minima are weighted equally and the scatter sets the errors, otherwise the
    errors are scaled by sqrt(chi2r) when chi2r > 1. `now_jd` defaults to the clock.
    Keys: n, cycles, oc_days, oc_min, mean_min and mean_err_min, slope_d_per_cycle and slope_err (None with
    fewer than 3 minima), drift_min_per_year, now_oc_min (the O−C line extrapolated to now: how far tonight's
    predictions are off) and verdict. Verdict "good": |mean| < 3 sigma and |now_oc_min| < `tolerance_min`;
    else "shifted"; "too few" with one minimum (no error to judge by). `tolerance_min` is a planning tolerance
    the user chooses, not a physical constant."""
    if len(minima_times) == 0:
        raise ValueError("no minima to compare with the catalogue ephemeris")
    errors = list(errors) if errors is not None else [None] * len(minima_times)
    kinds = list(kinds) if kinds is not None else ["I"] * len(minima_times)
    rows = sorted(zip(minima_times, errors, kinds, strict=True), key=lambda r: r[0])[-newest:]
    ms = [Minimum(float(t), e, k) for t, e, k in rows]
    cyc = epochs(ms, t0, period)
    oc = np.array([m.time for m in ms]) - t0 - cyc * period
    n = len(ms)
    err = np.array([e if e and e > 0 else np.nan for _, e, _ in rows], float)
    weighted = not np.isnan(err).any()
    w = 1 / err**2 if weighted else np.ones(n)
    floor = 1.0 if weighted else 0.0  # equal weights: the scatter itself is the error

    def scale(resid, dof):
        return max(floor, np.sqrt(np.sum(w * resid**2) / dof))

    mean = float(np.sum(w * oc) / np.sum(w))
    mean_err = float(scale(oc - mean, n - 1) / np.sqrt(np.sum(w))) if n > 1 else None
    xm = np.sum(w * cyc) / np.sum(w)
    sxx = np.sum(w * (cyc - xm) ** 2)
    slope = slope_err = None
    now_oc = mean
    if n >= 3 and sxx > 0:
        slope = float(np.sum(w * (cyc - xm) * oc) / sxx)
        slope_err = float(scale(oc - mean - slope * (cyc - xm), n - 2) / np.sqrt(sxx))
        now = time.time() / 86400 + 2440587.5 if now_jd is None else float(now_jd)
        now_oc = mean + slope * ((now - t0) / period - xm)
    good = mean_err is not None and abs(mean) < 3 * mean_err and abs(now_oc) * MIN_PER_DAY < tolerance_min
    return {
        "n": n, "cycles": cyc.tolist(), "oc_days": oc.tolist(), "oc_min": (oc * MIN_PER_DAY).tolist(),
        "mean_min": mean * MIN_PER_DAY, "mean_err_min": None if mean_err is None else mean_err * MIN_PER_DAY,
        "slope_d_per_cycle": slope, "slope_err": slope_err,
        "drift_min_per_year": None if slope is None else slope / period * 365.25 * MIN_PER_DAY,
        "now_oc_min": float(now_oc * MIN_PER_DAY),
        "verdict": "too few" if mean_err is None else "good" if good else "shifted",
    }  # fmt: skip
