"""Star-pattern matching, stacking of rotated frames, rotation by any angle and resampling."""

import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

from astrowb.calibration import starmatch as sm
from astrowb.calibration.stacking import stack
from astrowb.io import process

RNG = np.random.default_rng(8)
STARS = RNG.uniform(25, 175, (30, 2))
FLUX = RNG.uniform(3e3, 3e4, 30)


def rotation(angle_deg, scale=1.0):
    a = np.radians(angle_deg)
    return scale * np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])


def render(xy, shape=(200, 200), sigma=1.6):
    yy, xx = np.mgrid[: shape[0], : shape[1]]
    img = np.full(shape, 100.0)
    for (x, y), f in zip(xy, FLUX, strict=True):
        img += f / (2 * np.pi * sigma**2) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma**2))
    return (img + RNG.normal(0, 3, shape)).astype(np.float32)


def test_match_points_with_decoys_and_missing_stars():
    m_true, t_true = rotation(-123.0, 0.93), np.array([30.0, -12.0])
    img = STARS @ m_true.T + t_true + RNG.normal(0, 0.05, STARS.shape)
    img = np.vstack([img[3:], RNG.uniform(0, 200, (5, 2))])[RNG.permutation(32)]  # 3 lost, 5 new
    m, t, n, rms = sm.match(STARS, img)
    assert sm.describe(m) == pytest.approx((-123.0, 0.93), abs=0.02) and t == pytest.approx(t_true, abs=0.2)
    assert n >= 20 and rms < 0.2
    with pytest.raises(ValueError):
        sm.match(STARS, RNG.uniform(0, 200, (30, 2)))  # unrelated fields


def test_rotated_frames_stack_onto_the_first(tmp_path):
    c = np.array([100.0, 100.0])
    m_true = rotation(25.0, 1.03)
    frames = [STARS, (STARS - c) @ m_true.T + c + [4.0, -3.0]]
    paths = []
    for i, xy in enumerate(frames):
        fits.PrimaryHDU(render(xy)).writeto(tmp_path / f"r{i}.fits")
        paths.append(tmp_path / f"r{i}.fits")
    found = sm.stars(fits.getdata(paths[0]))
    assert len(found) >= 25
    m, _, _, _ = sm.match(found, sm.stars(fits.getdata(paths[1])))
    assert sm.describe(m) == pytest.approx((25.0, 1.03), abs=0.05)
    img, cnt, h = stack(paths, align="stars", method="mean", rejection="none")
    single = fits.getdata(paths[0])
    for x, y in STARS[:5]:  # each star lands where it is in the first frame
        xi, yi = int(round(x)), int(round(y))
        if cnt[yi, xi] == 2:
            assert img[yi - 2 : yi + 3, xi - 2 : xi + 3].max() > 0.7 * single[yi - 2 : yi + 3, xi - 2 : xi + 3].max()
    import re

    rot = [float(m) for v in h["HISTORY"] for m in re.findall(r"rot=([-+\d.]+)", str(v))]
    assert rot == [pytest.approx(25.0, abs=0.1)]
    shifted, _, _ = stack(paths, align="translation", method="mean", rejection="none")
    assert np.nanmax(shifted) < np.nanmax(img)  # without rotation the stars smear


def header_with_wcs(shape):
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [150.0, 20.0]
    w.wcs.crpix = [shape[1] / 2, shape[0] / 2]
    w.wcs.cd = [[-1e-4, 0], [0, 1e-4]]
    return w.to_header()


def test_rotate_any_angle_and_resample_keep_the_sky():
    img = render(STARS)
    h = header_with_wcs(img.shape)
    sky = WCS(h).pixel_to_world_values(*STARS[0])
    out, h2 = process.rotate(img, h, 33.0)
    new_xy = WCS(h2).world_to_pixel_values(*sky)
    peak = np.unravel_index(
        np.nanargmax(
            np.nan_to_num(out[int(new_xy[1]) - 3 : int(new_xy[1]) + 4, int(new_xy[0]) - 3 : int(new_xy[0]) + 4])
        ),
        (7, 7),
    )
    assert abs(peak[0] - 3) <= 1 and abs(peak[1] - 3) <= 1  # the star is where the new WCS says
    sq, _ = process.rotate(img, h, 90.0)
    r90, _ = process.rotate90(img, h, 1)
    assert np.allclose(sq[5:-5, 5:-5], r90[5:-5, 5:-5], atol=1e-3)  # the same as the exact 90 degree turn
    big, h3 = process.resample(img, h, 2.0)
    assert big.shape == (400, 400) and np.nansum(big) == pytest.approx(np.nansum(img), rel=0.01)
    xy2 = WCS(h3).world_to_pixel_values(*sky)
    assert np.allclose(xy2, 2 * STARS[0] + 0.5, atol=0.01)
    with pytest.raises(ValueError):
        process.resample(img, h, 0.0)
