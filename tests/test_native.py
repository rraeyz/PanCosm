"""ARC-9: every compiled routine equals its NumPy twin, and the program runs without them."""

import numpy as np
import pytest

from astrowb import native
from astrowb.spectroscopy import orbit

needs_native = pytest.mark.skipif(not native.available(), reason="compiled routines not built (tools/build_native.py)")


@needs_native
@pytest.mark.parametrize("e", [0.0, 0.1, 0.5, 0.9, 0.99])
def test_kepler_matches_its_twin(e):
    m = np.random.default_rng(int(e * 100)).uniform(-50, 50, 10_000)
    fast = native.use("kepler_e")(m, e)
    twin = orbit._eccentric_anomaly(m, e)
    assert np.allclose(fast, twin, rtol=0, atol=1e-12)
    assert np.allclose(fast - e * np.sin(fast), np.mod(m, 2 * np.pi), atol=1e-12)


@needs_native
def test_kepler_edges():
    f = native.use("kepler_e")
    assert f(np.array([]), 0.3).shape == (0,)
    out = f(np.array([np.nan, 1.0, np.inf]), 0.3)
    assert np.isnan(out[0]) and np.isfinite(out[1]) and np.isnan(out[2])
    with pytest.raises(ValueError, match="eccentricity"):
        f(np.array([1.0]), 1.0)
    big = np.linspace(0, 100, 50_001)  # the threaded path gives the same numbers
    assert np.array_equal(f(big, 0.4), np.concatenate([f(big[:25_000], 0.4), f(big[25_000:], 0.4)]))


def test_switched_off_the_twin_runs(monkeypatch):
    monkeypatch.setenv(native.ENV, "off")
    assert native.use("kepler_e") is None and "kepler" not in native.describe()
    m = np.linspace(0, 7, 5).reshape(5, 1)
    e_anomaly = orbit.eccentric_anomaly(m, 0.3)
    assert e_anomaly.shape == (5, 1) and np.allclose(e_anomaly - 0.3 * np.sin(e_anomaly), np.mod(m, 2 * np.pi))
    monkeypatch.setenv(native.ENV, "auto")
    if native.available():
        assert np.allclose(orbit.eccentric_anomaly(m, 0.3), e_anomaly, atol=1e-12)
