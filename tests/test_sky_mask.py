"""PHO-45: IRAF's histogram-centroid sky."""

import numpy as np
import pytest

from astrowb.photometry.aperture import sky_estimate


def test_histogram_centroid_finds_the_sky_under_a_star_wing():
    rng = np.random.default_rng(5)
    sigma = 5.0
    v = rng.normal(500.0, sigma, 2000)
    v[:150] += rng.uniform(10, 200, 150)  # a neighbour's wing in 7 % of the ring
    dx = dy = np.zeros(v.size)
    sky, sd, n = sky_estimate(v, dx, dy, "centroid")
    assert sky == pytest.approx(500.0, abs=0.2 * sigma)
    assert v.mean() - 500.0 > 1.5 * sigma  # the plain mean is pulled up
    assert sd == pytest.approx(sigma, rel=0.15) and 1700 < n < 2000


def test_histogram_centroid_of_a_constant_ring():
    assert sky_estimate(np.full(50, 7.0), np.zeros(50), np.zeros(50), "centroid")[:2] == (7.0, 0.0)
