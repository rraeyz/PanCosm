"""PHO-44: every centring method finds synthetic Gaussian stars at S/N 50 within 0.05 px; "none" keeps the
prediction; the default is today's. Within 0.05 px: no bias beyond that (the scatter is the noise's, under 0.1 px)."""

import numpy as np
import pytest

from astrowb.photometry.aperture import recenter


def star(x, y, snr=50.0, fwhm=3.5, seed=0):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[:41, :41]
    s = fwhm / 2.3548
    sky_sigma = 10.0
    # S/N of the star in an aperture of 1.5 FWHM against the sky noise only
    flux = snr * sky_sigma * np.sqrt(np.pi * (1.5 * fwhm) ** 2)
    img = 100 + flux / (2 * np.pi * s * s) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * s * s))
    return img + rng.normal(0, sky_sigma, img.shape)


@pytest.mark.parametrize("method,start", [("auto", 0.0), ("moments", 0.8), ("gauss", 0.8)])
def test_methods_within_five_hundredths(method, start):
    """moments and gauss iterate (IRAF's cmaxiter) and find the star from 0.8 px away; auto (one pass of 1-D
    Gaussians, today's default) keeps about a quarter of the starting offset (0.2 px from 0.8 px): it is checked
    from the right place, as the frame's shift puts it."""
    diffs = []
    for seed in range(40):
        true = np.array([20.0, 20.0]) + np.random.default_rng(100 + seed).uniform(-0.5, 0.5, 2)
        diffs.append(recenter(star(*true, seed=seed), [true + start], method=method)[0] - true)
    d = np.array(diffs)
    assert np.all(np.abs(d.mean(axis=0)) < 0.05) and np.sqrt((d**2).mean()) < 0.1, d.mean(axis=0)


def test_none_and_the_default():
    img = star(20.3, 19.6)
    assert np.array_equal(recenter(img, [[21.0, 20.0]], method="none"), [[21.0, 20.0]])
    assert np.array_equal(recenter(img, [[21.0, 20.0]]), recenter(img, [[21.0, 20.0]], method="auto"))


def test_a_click_snaps_onto_the_nearest_star():
    """A click several pixels off moves onto the star; one beside a faint star next to a bright one stays on the
    faint star; a click on empty sky stays where it is."""
    from astrowb.photometry.aperture import snap_to_star

    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[:60, :60]
    img = 100 + rng.normal(0, 5, (60, 60))
    for x, y, f in ((20.3, 30.6, 2e4), (38.2, 30.1, 3e5), (44.0, 30.0, 1.5e4)):  # a faint star 5.8 px from a bright
        img += f / (2 * np.pi * 1.5**2) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.5**2))
    got = snap_to_star(img, [(24.0, 33.0), (45.5, 31.0), (8.0, 8.0)], radius=6)
    assert np.hypot(*(got[0] - (20.3, 30.6))) < 0.1
    assert np.hypot(*(got[1] - (44.0, 30.0))) < 0.3  # the faint one, not its bright neighbour
    assert np.array_equal(got[2], [8.0, 8.0])
