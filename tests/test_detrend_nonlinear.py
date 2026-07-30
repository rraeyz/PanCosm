"""Non-linear detrending (PLAN 4.8 item 17): a curved trend is removed by degree 2, not by degree 1."""

import numpy as np
import pytest

from astrowb.photometry import differential as d


def test_quadratic_time_drift_removed_and_eclipse_kept():
    rng = np.random.default_rng(8)
    t = np.linspace(0, 0.3, 400)
    eclipse = 1 - 0.3 * np.exp(-0.5 * ((t - 0.15) / 0.012) ** 2)
    drift = np.exp(0.02 * (t - 0.15) / 0.15 + 0.06 * ((t - 0.15) / 0.15) ** 2)  # curved: e.g. a dewing corrector
    rel = eclipse * drift * (1 + rng.normal(0, 0.002, t.size))
    lin = d.detrend(rel, {"time": t}, exclude=(0.1, 0.2), time=t)
    quad = d.detrend(rel, {"time": t}, exclude=(0.1, 0.2), time=t, degree=2)
    assert quad["scatter_after"] < 0.6 * lin["scatter_after"] and quad["degree"] == 2
    flat = np.asarray(quad["rel_flux"])
    flat /= np.median(flat[np.abs(t - 0.15) > 0.05])
    assert np.std(flat - eclipse) < 0.003  # only the noise is left
    assert np.min(flat) == pytest.approx(0.7, abs=0.01)  # the depth is kept
    assert set(quad["coefficients"]) == {"time", "time^2"}
    assert quad["coefficients"]["time^2"] == pytest.approx(0.06 / 0.15**2, rel=0.15)


def test_degree_one_is_unchanged():
    t = np.linspace(0, 1, 50)
    rel = np.exp(-0.1 * t)
    a, b = d.detrend(rel, {"time": t}), d.detrend(rel, {"time": t}, degree=1)
    assert a == b and a["coefficients"]["time"] == pytest.approx(-0.1)
