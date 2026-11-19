import json

import numpy as np
import pytest

from astrowb.timeseries.catalogue_check import against

T0, P = 2455000.0, 0.5
NOW = T0 + 4000 * P


def _times(cycles, dp=0.0, dt=0.0):
    return [T0 + dt + c * (P + dp) for c in cycles]


def test_exact_ephemeris_is_good():
    cyc = list(range(3000, 3040, 4))
    r = against(_times(cyc), [0.0005] * 10, T0, P, now_jd=NOW)
    assert abs(r["mean_min"]) < 1e-3 and r["verdict"] == "good" and r["n"] == 10
    json.dumps(r)


def test_period_error_recovered_and_shifted():
    cyc = list(range(3000, 3040, 3))
    dp = 2e-6
    rng = np.random.default_rng(1)
    err = 1e-4
    times = np.array(_times(cyc, dp)) + rng.normal(0, err, len(cyc))
    r = against(times, [err] * len(cyc), T0, P, newest=10, now_jd=NOW)
    assert abs(r["slope_d_per_cycle"] - dp) < 3 * r["slope_err"]
    assert r["verdict"] == "shifted" and r["now_oc_min"] > 5


def test_secondaries_at_half_cycles_and_newest_only():
    cyc = [10, 3000.5, 3001, 3002.5]
    r = against(_times(cyc), None, T0, P, newest=3, kinds=["I", "II", "I", "II"], now_jd=NOW)
    assert r["cycles"] == [3000.5, 3001, 3002.5] and r["n"] == 3
    assert max(abs(x) for x in r["oc_days"]) < 1e-8


def test_no_minima_raises():
    with pytest.raises(ValueError, match="no minima"):
        against([], [], T0, P)


def test_one_minimum_is_too_few_to_judge():
    r = against([T0 + 100 * P], [0.0005], T0, P, now_jd=NOW)
    assert r["verdict"] == "too few"
