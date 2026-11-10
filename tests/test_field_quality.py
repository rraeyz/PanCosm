"""IMG-4: a known tilt (FWHM 2.0 → 3.0 px across x) and curvature recovered within 10 %; elongated stars at 30°
give their angle within 3°."""

import numpy as np
import pytest

from astrowb.io import field_quality

SHAPE = (400, 500)


def frame(fwhm_of, angle=0.0, ratio=1.0, n=300, seed=1):
    rng = np.random.default_rng(seed)
    yy, xx = np.indices(SHAPE)
    img = np.full(SHAPE, 200.0)
    a = np.radians(angle)
    for _ in range(n):
        x, y = rng.uniform(15, SHAPE[1] - 15), rng.uniform(15, SHAPE[0] - 15)
        s = fwhm_of(x, y) / 2.3548
        sx, sy = s / np.sqrt(ratio), s * np.sqrt(ratio)  # major axis along angle when ratio < 1
        sl = (slice(int(y) - 12, int(y) + 13), slice(int(x) - 12, int(x) + 13))
        dx, dy = xx[sl] - x, yy[sl] - y
        u, v = dx * np.cos(a) + dy * np.sin(a), -dx * np.sin(a) + dy * np.cos(a)
        img[sl] += rng.uniform(2e4, 8e4) / (2 * np.pi * sx * sy) * np.exp(-(u**2 / (2 * sx**2) + v**2 / (2 * sy**2)))
    return img + rng.normal(0, 4, SHAPE)


def test_tilt_and_curvature():
    tilted = field_quality.analyse(frame(lambda x, y: 2.0 + x / SHAPE[1]))  # 2.0 at the left, 3.0 at the right
    assert tilted["tilt_percent"] == pytest.approx(100 * 1.0 / 2.5, rel=0.1)  # 1 px across a 2.5 px centre
    assert abs(tilted["tilt_angle"] - 0) < 10 or abs(tilted["tilt_angle"] - 360) < 10  # softer towards +x

    def curved(x, y):
        r2 = ((x - SHAPE[1] / 2) / (SHAPE[1] / 2)) ** 2 + ((y - SHAPE[0] / 2) / (SHAPE[0] / 2)) ** 2
        return 2.2 + 0.4 * r2  # corners (r² = 2) 0.8 px softer than the centre

    bent = field_quality.analyse(frame(curved, seed=2))
    assert bent["curvature_percent"] == pytest.approx(100 * 0.8 / 2.2, rel=0.1)


def test_elongated_stars_at_30_degrees():
    q = field_quality.analyse(frame(lambda x, y: 2.6, angle=30.0, ratio=0.6, seed=3))
    assert abs(q["angle"] - 30.0) < 3 and q["elongation"] > 0.25
