"""PER-10: Fourier parameters with honest errors, rise time, skewness."""

import numpy as np
import pytest

from astrowb.timeseries import shape


def series(phase, a, phi):
    return 12.0 + sum(ak * np.sin(2 * np.pi * k * phase + pk) for k, (ak, pk) in enumerate(zip(a, phi, strict=True), 1))


A, PHI = [0.3, 0.15, 0.1, 0.05], [0.4, 2.0, 4.1, 1.0]


def test_the_parameters_and_their_errors():
    inside = {"R21": 0, "phi31": 0}
    for seed in range(200):
        rng = np.random.default_rng(seed)
        ph = rng.uniform(0, 1, 300)
        d = shape.decompose(ph, series(ph, A, PHI) + rng.normal(0, 0.02, ph.size), max_order=8)
        r21, e21 = d["R"][2]
        p31, e31 = d["phi_k1"][3]
        inside["R21"] += abs(r21 - 0.5) < e21
        truth31 = (4.1 - 3 * 0.4) % (2 * np.pi)
        inside["phi31"] += abs((p31 - truth31 + np.pi) % (2 * np.pi) - np.pi) < e31
    assert d["order"] >= 4
    assert all(0.6 <= v / 200 <= 0.76 for v in inside.values()), inside


def test_rise_time_and_skewness():
    ph = np.linspace(0, 1, 500, endpoint=False)
    # a sawtooth-like RRab: fast rise; in magnitudes the brightening is the fall of the value
    saw = sum(-((-1) ** k) / k * np.sin(2 * np.pi * k * ph) for k in range(1, 9)) * 0.2
    d = shape.decompose(ph, 12.0 + saw, order=8)
    assert shape.rise_time(d) < 0.25
    # a brief brightening (magnitudes fall): the brightness is skewed towards the rare high values
    pulse = shape.decompose(ph, 12 - 0.5 * np.exp(-0.5 * ((ph - 0.5) / 0.05) ** 2), order=10)
    assert shape.skewness(pulse) > 1
    sym = shape.decompose(ph, 12 + 0.3 * np.sin(2 * np.pi * ph), order=1)
    assert shape.rise_time(sym) == pytest.approx(0.5, abs=1e-3) and abs(shape.skewness(sym)) < 1e-6
