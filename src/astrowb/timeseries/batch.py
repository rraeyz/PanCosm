"""Period search for many stars (plans/period.md PER-17): one method over a list of light curves in threads, a
results row per star (best period, its false-alarm probability, the second peak and its relation to the first)."""

from concurrent.futures import ThreadPoolExecutor

import numpy as np

from .methods import gls
from .significance import fap_baluev, local_peaks


def one(name, t, y, err=None, p_min=0.05, p_max=None):
    t, y = np.asarray(t, float), np.asarray(y, float)
    periods, power, best = gls(t, y, err, p_min, p_max)
    peaks = local_peaks(1 / periods, power, n=2)
    second = float(periods[peaks[1]]) if len(peaks) > 1 else np.nan
    fap = fap_baluev(t - t.min(), y, err, float(power.max()), 1 / periods.max(), 1 / periods.min())
    return {"name": name, "period": float(best), "power": float(power.max()), "fap": fap, "second": second,
            "ratio": second / best if np.isfinite(second) else np.nan, "n": len(t)}  # fmt: skip


def search_all(curves, p_min=0.05, p_max=None, workers=4):
    """curves: [(name, t, y, err or None)] → rows in the input order."""
    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(lambda c: one(*c, p_min=p_min, p_max=p_max), curves))
