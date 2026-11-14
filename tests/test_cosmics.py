"""UF-12: the cosmic-ray cleaning gives astroscrappy's mask and cleaned frame bit for bit, faster."""

import astroscrappy
import numpy as np
import pytest

from astrowb.calibration.cosmics import detect_cosmics


def frame(seed, shape=(400, 520)):
    rng = np.random.default_rng(seed)
    ny, nx = shape
    yy, xx = np.mgrid[:ny, :nx]
    d = rng.normal(800.0, 12.0, shape)
    for _ in range(60):  # stars, two of them saturated
        y, x, f = rng.uniform(0, ny), rng.uniform(0, nx), rng.uniform(2e2, 4e4)
        d += f * np.exp(-((yy - y) ** 2 + (xx - x) ** 2) / (2 * 1.6**2))
    for _ in range(150):  # cosmic-ray hits and tracks, some at the edges, long ones needing a later pass
        y, x, n, a = rng.integers(0, ny), rng.integers(0, nx), rng.integers(1, 14), rng.uniform(0, np.pi)
        for k in range(n):
            j, i = int(round(y + k * np.sin(a))), int(round(x + k * np.cos(a)))
            if 0 <= j < ny and 0 <= i < nx:
                d[j, i] += rng.uniform(150, 8000)
    return np.minimum(d, 65535).astype(np.float32)


@pytest.mark.parametrize(("seed", "gain", "readnoise"), [(1, 1.0, 6.5), (2, 2.3, 9.0), (3, 0.6, 4.0)])
def test_same_mask_and_cleaned_frame_as_astroscrappy(seed, gain, readnoise):
    d = frame(seed)
    m0, c0 = astroscrappy.detect_cosmics(d, gain=gain, readnoise=readnoise)
    m, c = detect_cosmics(d, gain=gain, readnoise=readnoise)
    assert m0.sum() > 100  # the frame has work for every pass
    assert np.array_equal(m, m0) and np.array_equal(c, c0)


def test_a_clean_frame_stays_as_it_is():
    d = np.random.default_rng(0).normal(500.0, 10.0, (200, 200)).astype(np.float32)
    m, c = detect_cosmics(d)
    assert not m.any() and np.array_equal(c, d)
