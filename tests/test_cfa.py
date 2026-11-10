"""CAL-17: an equalised colour flat removes the flat panel's colour cast; a bilinear picture keeps each colour; the
superpixel green of a Bayer frame equals the mono truth within the noise."""

import numpy as np
import pytest

from astrowb.calibration import cfa
from astrowb.io.bayer import split

SHAPE = (120, 160)


def mosaic(r, g, b, pattern="RGGB"):
    m = np.empty(SHAPE)
    for k, colour in enumerate(pattern):
        dy, dx = divmod(k, 2)
        m[dy::2, dx::2] = {"R": r, "G": g, "B": b}[colour][dy::2, dx::2]
    return m


def test_the_panel_colour_cast_is_removed():
    rng = np.random.default_rng(1)
    vign = 1 - 0.1 * (np.hypot(*(np.indices(SHAPE) - np.array(SHAPE)[:, None, None] / 2)) / 100) ** 2
    flat = mosaic(18000 * vign, 30000 * vign, 12000 * vign) + rng.normal(0, 30, SHAPE)  # a reddish-green panel
    sky = mosaic(*(np.full(SHAPE, 1000.0) * vign,) * 3)  # a grey sky through the same optics
    raw = cfa.equalise(flat, "RGGB")
    corrected = sky / (raw / np.median(raw))
    channels = split(corrected, "RGGB")
    levels = [np.median(channels[c]) for c in "RGB"]
    assert max(levels) / min(levels) == pytest.approx(1.0, abs=0.01)  # grey again
    plain = split(sky / (flat / np.median(flat)), "RGGB")
    assert max(np.median(plain[c]) for c in "RGB") / min(np.median(plain[c]) for c in "RGB") > 2  # the cast


def test_the_picture_and_the_superpixel_green():
    rng = np.random.default_rng(2)
    yy, xx = np.indices(SHAPE)
    truth = 500 + 3 * xx + 2 * yy
    noisy = mosaic(truth * 0.5, truth, truth * 0.3) + rng.normal(0, 2, SHAPE)
    rgb = cfa.debayer(noisy, "RGGB")
    inner = (slice(4, -4), slice(4, -4))
    assert np.allclose(rgb[..., 1][inner], truth[inner], atol=8)
    assert np.allclose(rgb[..., 0][inner], 0.5 * truth[inner], atol=8)
    green = split(noisy, "RGGB")["G"]
    mono = 0.5 * (truth[0::2, 1::2] + truth[1::2, 0::2])
    assert np.std(green - mono) < 2.5  # the two greens averaged: the noise / √2
