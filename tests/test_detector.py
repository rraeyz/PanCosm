"""CAL-9: a synthetic camera — gain 1.8 e⁻/ADU, read noise 6.5 e⁻, 2 % non-linearity at 50 000 ADU, full well
61 000 ADU, shutter 12 ms — recovered within the plan's limits."""

import numpy as np
import pytest

from astrowb.calibration import detector

GAIN, RN, BIAS, FULL = 1.8, 6.5, 500.0, 61000.0
SHAPE = (400, 400)


def expose(rng, level_adu):
    """A frame of level_adu above the bias: photon noise in electrons, read noise, the bias, the well's limit."""
    electrons = rng.poisson(np.full(SHAPE, max(level_adu, 0) * GAIN)).astype(float)
    adu = electrons / GAIN + rng.normal(0, RN / GAIN, SHAPE) + BIAS
    return np.minimum(adu, FULL + BIAS)


def test_gain_and_read_noise_from_two_flats_and_two_biases():
    rng = np.random.default_rng(1)
    out = detector.gain_read_noise(expose(rng, 20000), expose(rng, 20000), expose(rng, 0), expose(rng, 0))
    assert out["gain"] == pytest.approx(GAIN, rel=0.03) and out["read_noise"] == pytest.approx(RN, rel=0.03)
    assert out["boxes"] == 16


def test_photon_transfer_finds_the_gain_and_the_full_well():
    rng = np.random.default_rng(2)
    levels = [2000, 6000, 12000, 20000, 30000, 40000, 50000, 58000, 64000, 70000]
    pairs = [(expose(rng, x), expose(rng, x)) for x in levels]
    ptc = detector.photon_transfer(pairs, expose(rng, 0), expose(rng, 0))
    assert ptc["gain"] == pytest.approx(GAIN, rel=0.03)
    assert ptc["full_well"] == pytest.approx(58000, rel=0.06)  # the variance turns over as the well fills


def test_linearity_and_the_shutter():
    t = np.array([1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20.0])
    rate = 2600.0  # ADU / s
    true = rate * (t + 0.012)  # the shutter adds 12 ms
    measured = true * (1 - 0.02 * (true / 50000) ** 2)  # 2 % low at 50 000 ADU
    lin = detector.linearity(t, measured)
    corrected = sum(c * measured ** (k + 1) for k, c in enumerate(lin["coefficients"]))
    i = int(np.argmin(np.abs(true - 50000)))
    assert corrected[i] / true[i] == pytest.approx(1.0, abs=0.003)
    # where 0.02 (m / 50000)² reaches 1 %; the "true" line from the low levels carries a little of the curve
    assert lin["limit_1pct"] == pytest.approx(35355, rel=0.06)
    short = np.array([0.05, 0.1, 0.2, 0.5, 1.0])
    assert detector.shutter_offset(short, rate * (short + 0.012)) == pytest.approx(0.012, abs=0.002)
