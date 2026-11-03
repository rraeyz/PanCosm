"""MOD-13: scans over a parameter with the others refitted."""

import numpy as np
import pytest
from test_model_fitting import TRUTH, make, model

from astrowb.models import scan


def test_a_sharp_minimum_and_a_shallow_one():
    s = make()
    got = scan.scan(s, model, "incl", np.linspace(84, 88, 17))
    assert got["best"] == pytest.approx(TRUTH["incl"], abs=0.1) and got["verdict"] == "sharp"
    assert got["low"] <= TRUTH["incl"] <= got["high"]
    assert s.params["incl"].free and s["incl"] == pytest.approx(got["best"])
    # a curve without its eclipses (outside them the light is normalised): j is not decided at all
    flat = make(seed=2)
    d = flat.data[0]
    keep = np.abs(((d.time + 0.25) % 0.5) - 0.25) > 0.15
    d.time, d.value, d.error = d.time[keep], d.value[keep], d.error[keep]
    assert scan.scan(flat, model, "j", np.linspace(0.3, 0.9, 7))["verdict"] == "shallow"
    grid = scan.scan2(make(), model, ("incl", "r2"), (np.linspace(85, 87, 3), np.linspace(0.11, 0.13, 3)))
    assert grid.shape == (3, 3) and np.unravel_index(np.argmin(grid), grid.shape) == (1, 1)
