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


def test_a_star_masked_out_of_the_ring():
    """A neighbour in the ring: clipping keeps its faint wings and biases the median up (on average over 20 noise
    draws); masked by position, the bias is a quarter of that and under 0.05 sigma."""
    from astrowb.photometry.aperture import measure, star_mask

    yy, xx = np.mgrid[:101, :101]
    x0, y0, sigma = 50.2, 49.8, 5.0
    stars = 2e5 / (8 * np.pi) * np.exp(-((xx - x0) ** 2 + (yy - y0) ** 2) / 8)
    stars += 1e5 / (18 * np.pi) * np.exp(-((xx - x0 - 14) ** 2 + (yy - y0 - 3) ** 2) / 18)
    mask = star_mask(xx.shape, [(x0 + 14, y0 + 3)], 15)
    plain, masked = [], []
    for seed in range(20):
        img = 300.0 + np.random.default_rng(seed).normal(0, sigma, xx.shape) + stars
        plain.append(float(np.ravel(measure(img, [(x0, y0)], 5, 10, 20)[2])[0]) - 300)
        masked.append(float(np.ravel(measure(img, [(x0, y0)], 5, 10, 20, sky_mask=mask)[2])[0]) - 300)
    assert np.mean(plain) > 4 * np.mean(masked) and np.mean(masked) < 0.05 * sigma
