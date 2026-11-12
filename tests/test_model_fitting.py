"""MOD-12: fitting a system with the analytic eclipse model; the history restores a row exactly."""

import numpy as np
import pytest

from astrowb.models import eb
from astrowb.models import fitting as ft
from astrowb.models import system as sm

TRUTH = {"r1": 0.18, "r2": 0.12, "incl": 86.0, "j": 0.6}


def model(v, d):
    if d.kind == "lc":
        return eb.light_curve(d.time, 1.0, 0.0, v["r1"], v["r2"], v["incl"], v["j"], 0.0, 90.0, (0.5, 0.2),
                              (0.5, 0.2))  # fmt: skip
    raise ValueError(d.kind)


def make(seed=1, start=None):
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 1, 1500)
    flux = 3.7 * model(TRUTH, sm.DataSet("lc", ph, ph)) + rng.normal(0, 0.004, ph.size)  # an unknown scale
    start = start or {"r1": 0.17, "r2": 0.13, "incl": 85.0, "j": 0.55}
    s = sm.System({k: sm.Parameter(k, v, True, *lim) for (k, v), lim in zip(start.items(),
                   [(0.01, 0.5), (0.01, 0.5), (70.0, 90.0), (0.05, 3.0)], strict=True)})  # fmt: skip
    s.data.append(sm.DataSet("lc", ph, flux, np.full(ph.size, 0.004)))
    return s


@pytest.mark.parametrize("optimiser", ["lm", "nelder_mead", "basin"])
def test_local_optimisers_recover_the_truth(optimiser):
    s = make()
    hist = ft.History()
    row = ft.fit(s, model, optimiser, history=hist)
    assert row.chi2_after < row.chi2_before and row.chi2_after / 1500 < 1.1
    for k, v in TRUTH.items():
        assert s[k] == pytest.approx(v, abs=4 * row.errors[k] + 1e-3), k


def test_careful_from_a_poor_start_and_the_history():
    s = make(start={"r1": 0.3, "r2": 0.05, "incl": 80.0, "j": 1.5})
    hist = ft.History()
    first = ft.fit(s, model, "lm", history=hist)
    ft.fit(s, model, "careful", geometric=("r1", "r2", "incl"), history=hist)
    assert hist.rows[1].chi2_after <= first.chi2_after
    assert s["incl"] == pytest.approx(86.0, abs=0.3)
    hist.restore(s, 0)
    assert {k: s[k] for k in TRUTH} == {k: first.values[k] for k in TRUTH}
    with pytest.raises(ValueError):
        ft.fit(s, model, "simplex")
