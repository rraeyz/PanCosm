"""CAL-4: a two-amplifier frame with different bias levels and gains joins into a seamless sky (the step at the
boundary below 0.1σ)."""

import numpy as np
from astropy.io import fits

from astrowb.calibration import amplifiers


def test_two_amplifiers_join_seamlessly():
    rng = np.random.default_rng(3)
    ny = 120
    raw = np.zeros((ny, 240))
    sky_e = 3000.0  # electrons per pixel, the same everywhere on the sky
    for x0, x1, b0, b1, bias, gain in ((0, 100, 200, 220, 500.0, 1.5), (100, 200, 220, 240, 520.0, 1.8)):
        electrons = rng.poisson(sky_e, (ny, x1 - x0))
        raw[:, x0:x1] = electrons / gain + bias + rng.normal(0, 3, (ny, x1 - x0)) + np.linspace(0, 2, ny)[:, None]
        raw[:, b0:b1] = bias + rng.normal(0, 3, (ny, b1 - b0)) + np.linspace(0, 2, ny)[:, None]  # the overscan
    h = fits.Header({"DATASEC1": "[1:100,1:120]", "BIASSEC1": "[201:220,1:120]", "GAIN1": 1.5,
                     "DATASEC2": "[101:200,1:120]", "BIASSEC2": "[221:240,1:120]", "GAIN2": 1.8})  # fmt: skip
    assert [a["n"] for a in amplifiers.layout(h)] == [1, 2]
    out = amplifiers.join(raw, h)
    assert out.shape == (120, 200)
    left, right = out[:, 90:100], out[:, 100:110]
    sigma = np.std(out[:, :90])
    step = abs(np.mean(right) - np.mean(left))
    assert step < 0.1 * sigma, (step, sigma)
    assert abs(np.mean(out) - sky_e / 1.5) < 2  # in ADU of the first amplifier
    assert amplifiers.join(raw, fits.Header({"DATASEC": "[1:100,1:120]"})) is None
