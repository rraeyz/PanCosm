"""PHO-21: an object of constant brightness moving 300 px through a star field gives a flat curve, with the frames
where it passes a star flagged."""

import numpy as np
import pytest

from astrowb.photometry import moving_lc

ZP0 = 23.0


def scene(rng, shape=(220, 420)):
    n = 120
    xy = np.column_stack([rng.uniform(15, shape[1] - 15, n), rng.uniform(15, shape[0] - 15, n)])
    mags = rng.uniform(11.5, 16.5, n)
    # one bright star right on the track, so some frames are blended
    xy[0], mags[0] = (210.0, 110.4), 12.0
    return xy, mags


def render(shape, xy, flux, sky, rng, sigma=1.6):
    yy, xx = np.indices(shape)
    img = np.full(shape, sky)
    for (x, y), f in zip(xy, flux, strict=True):
        sl = (slice(max(0, int(y) - 10), int(y) + 11), slice(max(0, int(x) - 10), int(x) + 11))
        img[sl] += f / (2 * np.pi * sigma**2) * np.exp(-((xx[sl] - x) ** 2 + (yy[sl] - y) ** 2) / (2 * sigma**2))
    return rng.poisson(img).astype(float)


def test_a_constant_object_across_the_field():
    rng = np.random.default_rng(8)
    shape = (220, 420)
    xy, mags = scene(rng)
    times = np.linspace(0, 0.2, 40)
    track = moving_lc.linear_track(times, (0.0, 60.0, 110.0), (0.2, 360.0, 110.0))  # 300 px
    obj_mag = 13.5
    frames, fields = [], []
    for k, (x, y) in enumerate(track):
        zp = ZP0 - 0.2 * k / 40 + rng.normal(0, 0.01)  # extinction and thin cloud change the zero point
        flux = 10 ** (-0.4 * (np.r_[mags, obj_mag] - zp))
        frames.append(render(shape, np.vstack([xy, [x, y]]), flux, 200.0, rng))
        on = (xy[:, 0] > 20) & (xy[:, 0] < shape[1] - 20) & (xy[:, 1] > 20) & (xy[:, 1] < shape[0] - 20)
        fields.append([(a, b, m) for (a, b), m in zip(xy[on], mags[on], strict=True)])
    rows = moving_lc.measure(frames, track, fields, 5.0, 10.0, 15.0)
    flagged = np.array([r["blended"] for r in rows])
    near = np.hypot(track[:, 0] - 210.0, track[:, 1] - 110.4) < 15.0
    assert np.array_equal(flagged[near], near[near]) and near.sum() >= 2
    clean = ~flagged
    mag = np.array([r["mag"] for r in rows])[clean]
    err = np.array([r["err"] for r in rows])[clean]
    assert np.mean(mag) == pytest.approx(obj_mag, abs=0.01)
    assert np.std(mag) < 1.2 * np.sqrt(np.mean(err**2))  # flat to its predicted error


def test_reduced_magnitude_and_light_time():
    assert moving_lc.reduced(15.0, 2.0, 1.0) == pytest.approx(15.0 - 5 * np.log10(2.0))
    assert moving_lc.light_time(2461000.5, 1.0) == pytest.approx(2461000.5 - 499.004784 / 86400, abs=1e-8)
