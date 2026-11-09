"""CAL-12: a faint trail (2σ per pixel) across a 2k frame found with its angle within 0.3°; none on a clean frame."""

import numpy as np
import pytest

from astrowb.calibration import trails


def frame(seed, angle=None, amp=20.0, shape=(2048, 2048)):
    rng = np.random.default_rng(seed)
    img = rng.normal(1000.0, 10.0, shape)
    ny, nx = shape
    for _ in range(400):  # stars
        y, x = rng.integers(10, ny - 10), rng.integers(10, nx - 10)
        img[y - 2 : y + 3, x - 2 : x + 3] += rng.uniform(100, 20000)
    if angle is not None:
        yy, xx = np.indices(shape)
        a = np.radians(angle)
        d = -(xx - (nx - 1) / 2) * np.sin(a) + (yy - (ny - 1) / 2) * np.cos(a) - 150.0
        img += amp * np.exp(-(d**2) / (2 * 1.5**2))
    return img


@pytest.mark.parametrize("angle", [33.7, 121.2])
def test_a_faint_trail_is_found(angle):
    t = trails.find(frame(1, angle))
    assert t is not None and abs((t["angle"] - angle + 90) % 180 - 90) < 0.3
    assert abs(t["offset"] - 150.0) < 6
    mask = trails.band((2048, 2048), t)
    assert 0.002 < mask.mean() < 0.02  # a band, not the frame


def test_no_trail_on_a_clean_frame():
    assert trails.find(frame(2)) is None


def test_a_bright_trail_too():
    t = trails.find(frame(3, 64.0, amp=3000.0))
    assert t is not None and abs(t["angle"] - 64.0) < 0.3
