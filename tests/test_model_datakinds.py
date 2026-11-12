"""MOD-17: times of minimum and a light-ratio constraint in the same fit."""

import numpy as np
import pytest

from astrowb.models import eb
from astrowb.models import fitting as ft
from astrowb.models import system as sm

T0, P = 2459000.1234, 1.234567


def model(v, d):
    if d.kind == "lc":
        ph = (d.time - (v["t0"] - T0)) / v["period"] * P  # times relative to T0, in the reference period's phase
        return eb.light_curve(ph / P, 1.0, 0.0, v["r1"], v["r2"], 86.0, v["j"], 0.0, 90.0, (0.5, 0.2), (0.5, 0.2))
    return v["t0"] - T0 + v["period"] * d.time  # minima: relative to T0


def make(seed=0):
    rng = np.random.default_rng(seed)
    t = rng.uniform(0, 3 * P, 800)
    truth = {"t0": T0, "period": P, "r1": 0.18, "r2": 0.12, "j": 0.6}
    s = sm.System({"t0": sm.Parameter("t0", T0 + 0.001, True), "period": sm.Parameter("period", P + 2e-5, True),
                   "r1": sm.Parameter("r1", 0.17, True, 0.01, 0.5), "r2": sm.Parameter("r2", 0.13, True, 0.01, 0.5),
                   "j": sm.Parameter("j", 0.5, True, 0.05, 3.0)})  # fmt: skip
    flux = model(truth, sm.DataSet("lc", t, t)) + rng.normal(0, 0.01, t.size)
    s.data.append(sm.DataSet("lc", t, flux, np.full(t.size, 0.01)))
    return s, truth


def test_minima_pin_the_ephemeris_and_a_light_ratio_narrows_j():
    s, truth = make()
    alone = ft.fit(s, model, "lm")
    epochs = np.arange(-3000, 3001, 500.0)
    rng = np.random.default_rng(1)
    s2, _ = make()
    s2.data.append(sm.DataSet("minima", epochs, P * epochs + rng.normal(0, 2e-4, epochs.size),
                              np.full(epochs.size, 2e-4)))  # fmt: skip
    both = ft.fit(s2, model, "lm")
    assert both.errors["period"] < alone.errors["period"] / 50
    assert s2["period"] == pytest.approx(P, abs=4 * both.errors["period"])
    s3, _ = make()
    ratio = eb.light_ratio(0.18, 0.12, 0.6, (0.5, 0.2), (0.5, 0.2))
    s3.constraints.append(("L2/L1", lambda v: eb.light_ratio(v["r1"], v["r2"], v["j"], (0.5, 0.2), (0.5, 0.2)),
                           ratio, 0.005))  # fmt: skip
    constrained = ft.fit(s3, model, "lm")
    assert constrained.errors["j"] < alone.errors["j"]
