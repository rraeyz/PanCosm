"""OC-3: many minima from long or sparse series by the star's own template."""

import time

import numpy as np

from astrowb.timeseries.ephemeris import Minimum
from astrowb.timeseries.etv import chunk_times, eclipse_times
from astrowb.timeseries.oc_models import fit_ltte

P, T0 = 1.3, 2459000.3


def light_curve(t, amp, p3):
    """A detached binary (primary 30 %, secondary 10 %) whose eclipses come early and late with a sine of amp days."""
    out = np.ones_like(t)
    for shift, depth in ((0.0, 0.3), (0.5, 0.1)):
        n = np.round((t - T0) / P - shift)
        mid = T0 + (n + shift) * P + amp * np.sin(2 * np.pi * (t - T0) / p3)
        out -= depth * np.exp(-0.5 * ((t - mid) / 0.03) ** 2)
    return out


def test_dense_series_one_time_per_eclipse_with_honest_errors():
    """Two TESS sectors at 2-min cadence with a 30 s timing wave: every eclipse timed, the scatter about the wave
    equal to the reported errors, in well under a second per hundred eclipses."""
    t = np.arange(T0, T0 + 54, 2 / 1440)
    y = light_curve(t, 30 / 86400, 20.0) + np.random.default_rng(1).normal(0, 0.002, t.size)
    start = time.perf_counter()
    minima = eclipse_times(t, y, T0, P)
    took = time.perf_counter() - start
    primaries = [(tm, e) for tm, e, k in minima if k == "I"]
    assert len(primaries) >= 40 and len(minima) >= 80 and took < 5
    tm, e = np.array(primaries).T
    oc = tm - (T0 + np.round((tm - T0) / P) * P)
    resid = oc - 30 / 86400 * np.sin(2 * np.pi * (tm - T0) / 20.0)
    assert abs(np.mean(resid)) < 3 * np.std(resid) / np.sqrt(len(resid))
    assert 0.7 < np.median(e) / np.std(resid) < 1.4


def test_sparse_survey_chunks_recover_a_third_body():
    """1200 survey points over 8 years, a 0.01 d light-travel-time wave of 1500 days: the times of the chunks
    give back its amplitude and period within 2 σ (with 300 points, as the plan first asked, ten chunks are too
    few for the seven parameters: the period aliases)."""
    rng = np.random.default_rng(3)
    t = np.sort(rng.uniform(T0, T0 + 8 * 365, 1200))
    y = light_curve(t, 0.01, 1500) + rng.normal(0, 0.01, t.size)
    chunks = chunk_times(t, y, T0, P)
    assert len(chunks) >= 30 and {k for *_, k in chunks} == {"I", "II"}
    fit = fit_ltte([Minimum(tm, e, k) for tm, e, k in chunks], T0, P, p3_range=(300, 3000))
    assert abs(fit.amplitude - 0.01) < 2 * fit.errors["amplitude"]
    assert abs(fit.p3 - 1500) < 2 * fit.errors["p3"]
