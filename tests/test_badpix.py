"""CAL-8: a bad column, 300 hot pixels and a dead cluster all masked from dark + flat; both file formats write and
read back identically; repairs within 1σ on a smooth sky; "none" leaves the data alone."""

import numpy as np
import pytest

from astrowb.calibration import badpix

SHAPE = (200, 240)


def masters_with_defects(rng):
    dark = 300 + rng.normal(0, 2, SHAPE)
    flat = 1 + rng.normal(0, 0.003, SHAPE)
    truth = np.zeros(SHAPE, bool)
    ys, xs = rng.integers(0, SHAPE[0], 300), rng.integers(0, SHAPE[1], 300)
    dark[ys, xs] += rng.uniform(100, 3000, 300)
    truth[ys, xs] = True
    dark[:, 77] += 15  # a bad column, warm all along
    truth[:, 77] = True
    flat[120:124, 30:35] = 0.05  # a dead cluster
    truth[120:124, 30:35] = True
    return dark, flat, truth


def test_every_defect_masked():
    dark, flat, truth = masters_with_defects(np.random.default_rng(1))
    mask = badpix.from_masters(dark, flat)
    assert mask[truth].all()  # all of them
    assert (mask & ~truth).sum() < 0.001 * mask.size  # and hardly anything else


@pytest.mark.parametrize("suffix", [".fits", ".txt"])
def test_both_formats_round_trip(tmp_path, suffix):
    dark, flat, _ = masters_with_defects(np.random.default_rng(2))
    mask = badpix.from_masters(dark, flat)
    path = badpix.write(tmp_path / f"mask{suffix}", mask)
    assert np.array_equal(badpix.read(path, SHAPE), mask)


def test_repairs_on_a_smooth_sky():
    rng = np.random.default_rng(3)
    yy, xx = np.indices(SHAPE)
    sky = 1000 + 0.5 * xx + 0.3 * yy
    data = sky + rng.normal(0, 5, SHAPE)
    mask = np.zeros(SHAPE, bool)
    mask[:, 77] = True
    mask[50:53, 100:103] = True
    broken = data.copy()
    broken[mask] = 60000
    for mode in ("neighbours", "columns"):
        fixed = badpix.repair(broken, mask, mode)
        assert np.all(np.abs(fixed[mask] - sky[mask]) < 3 * 5)  # within the noise (3σ for every one of them)
        assert np.sqrt(np.mean((fixed[mask] - sky[mask]) ** 2)) < 5  # 1σ in the mean
    assert np.array_equal(badpix.repair(broken, mask, "none"), broken)
