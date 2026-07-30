"""PLAN 4.8 item 11: every change made for speed gives the result of the slow, plain way (full frame, float64).
Numbers may differ only in the last digits of a double (summation order) or a fit's convergence (1e-6)."""

import numpy as np
import pytest
from photutils.psf import CircularGaussianPRF

from astrowb.io import inspect as ins

NY, NX = 700, 800


def field(fwhm, x, y, seed=1):
    yy, xx = np.mgrid[:NY, :NX]
    img = np.full((NY, NX), 1000.0)
    for sx, sy, f in ((x + 0.3, y - 0.2, 5e6), (x + 40, y + 25, 1e6)):
        img += CircularGaussianPRF(flux=f, x_0=sx, y_0=sy, fwhm=fwhm)(xx, yy)
    return img + np.random.default_rng(seed).normal(0, 8, img.shape)


@pytest.mark.parametrize(
    "fwhm, x, y, radii",
    [
        (3.0, 400, 350, {}),
        (3.0, 12, 30, {}),  # at the corner: the cut is clipped by the frame
        (25.0, 400, 350, {}),
        (35.0, 400, 350, {}),
        (60.0, 400, 350, {}),  # a defocused star: the sky annulus is wider than the first cut
        (4.0, 400, 350, {"r_ap": 10, "r_in": 60, "r_out": 140}),
    ],
)
def test_star_on_a_cut_equals_star_on_the_full_frame(fwhm, x, y, radii):
    img = field(fwhm, x, y)
    fast = ins.star_info(img, x, y, **radii)
    full = ins._star_info(img, x, y, radii.get("r_ap"), radii.get("r_in"), radii.get("r_out"), 1.0, None, None)
    for key, value in full.items():
        if isinstance(value, float) and np.isfinite(value):
            tol = 1e-6 if key in ("fwhm",) else 1e-10
            assert fast[key] == pytest.approx(value, rel=tol, abs=1e-9), key


@pytest.mark.parametrize("dtype", [np.float32, np.float64, np.uint16, np.int32])
def test_area_statistics_equal_the_float64_computation(dtype):
    rng = np.random.default_rng(3)
    data = (rng.normal(1200, 40, (300, 400)) + rng.uniform(0, 1, (300, 400))).astype(dtype)
    if np.issubdtype(dtype, np.floating):
        data[5, 7] = np.nan  # an invalid pixel: left out the same way
    got = ins.area_stats(data, 3, 2, 250, 199)
    box = np.asarray(data[2:200, 3:251], np.float64)
    vals = box[np.isfinite(box)]
    exact = {
        "pixels": vals.size,
        "sum": vals.sum(),
        "mean": vals.mean(),
        "median": np.median(vals),
        "std": vals.std(ddof=1),
        "mad_std": 1.4826 * np.median(np.abs(vals - np.median(vals))),
        "min": vals.min(),
        "max": vals.max(),
    }
    for key, value in exact.items():
        # float32 data: the median and MAD are taken in the data's own precision (7 digits), below its noise
        rel = 1e-6 if dtype == np.float32 and key in ("median", "mad_std") else 1e-12
        assert got[key] == pytest.approx(value, rel=rel), key
    iy, ix = np.unravel_index(np.nanargmax(box), box.shape)
    assert got["max_xy"] == (3 + ix, 2 + iy)


def test_histogram_limits_from_a_sample_match_the_full_percentiles():
    v = np.random.default_rng(4).lognormal(7, 0.5, 4_000_000).astype(np.float32)
    edges = ins.histogram(v, bins=200, clip=(0.5, 99.5))["edges"]
    lo, hi = np.percentile(v, (0.5, 99.5))
    width = (hi - lo) / 200
    assert abs(edges[0] - lo) < width and abs(edges[-1] - hi) < width  # display limits within one bin
