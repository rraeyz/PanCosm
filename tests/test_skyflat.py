"""CAL-11: a dome flat with a 3 % illumination gradient the sky does not have — after the correction from the night
sky, a star dithered across the field is constant within 0.3 % (it was 3 %)."""

import numpy as np
import pytest

from astrowb.calibration import skyflat
from astrowb.photometry.aperture import measure

SHAPE = (200, 260)


def scene(rng):
    yy, xx = np.indices(SHAPE)
    pixels = 1 + rng.normal(0, 0.01, SHAPE)  # the detector's pixel-to-pixel response, in every flat alike
    vign = 1 - 0.08 * (np.hypot(xx - 130, yy - 100) / 165) ** 2  # the telescope's vignetting, seen by sky and dome
    dome_extra = 1 + 0.03 * (xx / SHAPE[1] - 0.5) * 2  # the dome lamp lights one side 3 % more
    response = pixels * vign
    dome_flat = 30000 * response * dome_extra + rng.normal(0, 20, SHAPE)
    return response, dome_flat


def light(rng, response, offset, star_xy):
    yy, xx = np.indices(SHAPE)
    sky = np.full(SHAPE, 800.0)
    stars = [(60 + offset[0], 50 + offset[1], 5e4), (180 + offset[0], 140 + offset[1], 8e4), (*star_xy, 2e6)]
    for x, y, f in stars:
        sky = sky + f / (2 * np.pi * 2.0**2) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 2.0**2))
    return rng.poisson(sky * response).astype(float)


def test_the_sky_corrects_the_dome_flat():
    rng = np.random.default_rng(4)
    response, dome = scene(rng)
    offsets = [(dx, dy) for dx in (-40, 0, 40) for dy in (-30, 0, 30)]
    frames, places = [], []
    for k, off in enumerate(offsets):
        star = (40 + 22 * k, 100 + (k % 3) * 5)  # the star of interest walks across the field
        frames.append(light(rng, response, off, star))
        places.append(star)
    sky = skyflat.super_sky(frames, offsets)
    illum = skyflat.illumination(sky, dome)
    corrected = dome * illum

    def spread(flat):
        norm = flat / np.median(flat)
        f = [measure(frame / norm, [p], 6, 12, 18)[0][0] for frame, p in zip(frames, places, strict=True)]
        return np.std(f) / np.mean(f)

    assert spread(dome) > 0.01  # the dome flat leaves the star's flux walking with it (±3 % across)
    assert spread(corrected) < 0.003  # within 0.3 % after the correction


def test_small_dithers_are_refused():
    assert skyflat.check_dithers([(0, 0), (2, 1), (1, 3), (3, 0), (0, 2)], star_size_px=10) is not None
    assert skyflat.check_dithers([(0, 0), (40, 0), (0, 40), (40, 40), (20, 20)], star_size_px=10) is None
    with pytest.raises(ValueError):
        skyflat.super_sky([np.ones((10, 10))] * 5, [(0, 0)] * 5)
