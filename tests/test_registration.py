"""CAL-15: frames turned by 0.7°, scaled by 1.002 and with barrel distortion are registered with their stars within
0.05 px and the stars' flux kept within 0.2 %."""

import numpy as np
import pytest

from astrowb.calibration import registration
from astrowb.photometry.aperture import measure, recenter

SHAPE = (220, 260)


def truth(xy):
    """Reference pixels → the frame's: rotation 0.7°, scale 1.002, a shift, and barrel distortion."""
    c = np.array([130.0, 110.0])
    u = xy - c
    a = np.radians(0.7)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    v = 1.002 * u @ rot.T
    r2 = np.sum(v**2, axis=1, keepdims=True)
    v = v * (1 + 2e-7 * r2)  # ~0.4 px at the corners
    return v + c + [3.3, -2.1]


def render(xy, flux, sigma=1.8):
    yy, xx = np.indices(SHAPE)
    img = np.full(SHAPE, 100.0)
    for (x, y), f in zip(xy, flux, strict=True):
        img += f / (2 * np.pi * sigma**2) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * sigma**2))
    return img


def test_a_turned_scaled_distorted_frame_registers():
    rng = np.random.default_rng(1)
    ref_xy = rng.uniform(25, [235, 195], (60, 2))
    flux = rng.uniform(2e4, 1e5, 60)
    frame = render(truth(ref_xy), flux)  # the same stars, the same counts each (spread a little wider)
    measured = truth(ref_xy) + rng.normal(0, 0.02, ref_xy.shape)  # star centres found on the frame
    model = registration.fit(ref_xy, measured, "auto")
    assert model.kind in ("poly2", "poly3", "homography") and model.rms < 0.05
    for kernel, tol in (("bicubic", 0.002), ("lanczos3", 0.002)):
        out = registration.resample(frame, model, SHAPE, kernel)
        d = np.hypot(*(ref_xy[:, None, :] - ref_xy[None, :, :]).transpose(2, 0, 1)) + np.eye(len(ref_xy)) * 1e9
        alone = d.min(axis=1) > 12  # a blended pair's centroid says nothing about the registration
        inner = np.all((ref_xy > 35) & (ref_xy < np.array([225, 185])), axis=1) & alone
        found = recenter(np.nan_to_num(out, nan=100.0), ref_xy[inner], 9)
        assert np.sqrt(np.mean(np.sum((found - ref_xy[inner]) ** 2, axis=1))) < 0.05
        f_out = measure(np.nan_to_num(out, nan=100.0), ref_xy[inner], 8, 14, 20)[0]
        assert np.median(np.abs(f_out / flux[inner] - 1)) < tol, kernel


def test_the_simplest_kind_for_a_pure_shift():
    ref = np.random.default_rng(2).uniform(0, 200, (20, 2))
    model = registration.fit(ref, ref + [1.5, -0.7])
    assert model.kind == "shift" and model.rms < 1e-9
    with pytest.raises(ValueError):
        registration.fit(ref[:1], ref[:1], "affine")
