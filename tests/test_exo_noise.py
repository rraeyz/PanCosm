"""EXO-13: the β factor finds red noise and leaves white noise alone."""

import numpy as np
import pytest

from astrowb.exoplanets import noise


def test_beta_on_white_and_red_noise():
    rng = np.random.default_rng(0)
    white = rng.normal(0, 1e-3, 3000)
    assert noise.beta_factor(white, [10, 15, 20, 30]) == pytest.approx(1.0, abs=0.15)
    red = white + np.convolve(rng.normal(0, 4e-4, 3000), np.ones(40) / np.sqrt(40), "same")
    assert noise.beta_factor(red, [10, 15, 20, 30]) > 1.5
    assert noise.scale_to_chi2(white, np.full(3000, 5e-4), 3) == pytest.approx(2.0, rel=0.05)
    assert noise.scale_to_chi2(white, np.full(3000, 2e-3), 3) == 1.0
