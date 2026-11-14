"""CAL-16: frames chosen by their quality, weights, and a 2 × 2 mosaic of fields whose backgrounds differ joins
with seams below 0.3σ."""

import numpy as np
import pytest

from astrowb.calibration import mosaic


def test_selection_and_weights():
    stats = [{"fwhm": 2.1, "background": 300, "stars": 120, "noise": 10.0},
             {"fwhm": 3.8, "background": 310, "stars": 80, "noise": 12.0},
             {"fwhm": 2.4, "background": 900, "stars": 30, "noise": 25.0},  # twilight
             {"fwhm": 2.0, "background": 305, "stars": 125, "noise": 9.5}]  # fmt: skip
    assert mosaic.select(stats, best=0.5).tolist() == [True, False, False, True]
    assert mosaic.select(stats, max_background=500, max_fwhm=3.0).tolist() == [True, False, False, True]
    w = mosaic.weights(stats, "noise")
    assert w.mean() == pytest.approx(1.0) and w[3] > w[0] > w[1] > w[2]
    with pytest.raises(ValueError):
        mosaic.weights(stats, "magic")


def test_a_two_by_two_mosaic_without_seams():
    rng = np.random.default_rng(4)
    sky = 1000.0
    field = np.full((180, 230), sky)
    yy, xx = np.indices(field.shape)
    for _ in range(40):
        x, y = rng.uniform(0, 230), rng.uniform(0, 180)
        field += 2e4 / (2 * np.pi * 4) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / 8)
    offsets = [(0, 0), (110, 0), (0, 80), (110, 80)]
    tiles = []
    for k, (ox, oy) in enumerate(offsets):
        part = field[oy : oy + 100, ox : ox + 120].copy()
        tiles.append(part + 37.0 * k + rng.normal(0, 5, part.shape))  # each field's sky a little different
    image = mosaic.join(tiles, offsets, field.shape)
    sigma = 5.0
    for x in (110, 120):  # across the vertical seams of the overlap's edges
        assert abs(np.nanmedian(image[:, x - 3 : x]) - np.nanmedian(image[:, x : x + 3])) < 0.3 * sigma
    for y in (80, 100):
        assert abs(np.nanmedian(image[y - 3 : y, :]) - np.nanmedian(image[y : y + 3, :])) < 0.3 * sigma
