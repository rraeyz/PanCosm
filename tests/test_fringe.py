"""CAL-10: fringes of 3 % of the sky on dithered star fields — below 0.3 % after the correction, the stars' fluxes
unbiased."""

import numpy as np

from astrowb.calibration import fringe
from astrowb.photometry.aperture import measure

SHAPE = (200, 240)


def pattern():
    yy, xx = np.indices(SHAPE)
    return 0.03 * np.sin(xx / 3.0 + 0.4 * np.sin(yy / 6.0)) * np.cos(yy / 4.0)  # wavy lines ~20 px apart


def frame(rng, offset, amp=1.0, stars=None):
    yy, xx = np.indices(SHAPE)
    sky = 2000.0
    img = sky * (1 + amp * pattern())
    for x, y, f in stars or []:
        x, y = x + offset[0], y + offset[1]
        img = img + f / (2 * np.pi * 1.8**2) * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 1.8**2))
    return rng.normal(img, np.sqrt(img))


def test_fringes_removed_and_stars_unbiased():
    rng = np.random.default_rng(5)
    stars = [(float(x), float(y), float(f)) for x, y, f in zip(rng.uniform(30, 210, 25), rng.uniform(30, 170, 25),
                                                             rng.uniform(5e4, 2e5, 25), strict=True)]  # fmt: skip
    offsets = [(dx, dy) for dx in (-20, 0, 20) for dy in (-15, 15)]
    lights = [frame(rng, off, 1.0, stars) for off in offsets]
    f = fringe.make_fringe_frame(lights)
    target = frame(rng, (5, 5), amp=0.8, stars=stars)  # this frame's fringes a little weaker
    scale = np.sum(f * pattern()) / np.sum(pattern() ** 2)  # how strong the (smoothed) fringe frame is
    assert abs(fringe.fit_amplitude(target, f) * scale - 0.8) < 0.05  # the frame's 0.8, found
    fixed = fringe.remove(target, f)
    inner = (slice(25, -25), slice(25, -25))
    star_free = np.ones(SHAPE, bool)
    yy, xx = np.indices(SHAPE)
    for x, y, _ in stars:
        star_free &= np.hypot(xx - x - 5, yy - y - 5) > 10
    before = np.std((target / 2000 - 1)[inner][star_free[inner]])
    after_noise = np.std((fixed / 2000 - 1)[inner][star_free[inner]])
    photon = 1 / np.sqrt(2000)
    residual = np.sqrt(max(after_noise**2 - photon**2, 0))
    assert before > 0.015 and residual < 0.003  # 3 % fringes down below 0.3 %
    xy = [(x + 5, y + 5) for x, y, _ in stars]
    truth = np.array([s[2] for s in stars])
    flux = measure(fixed, xy, 6, 12, 18)[0]
    assert abs(np.median(flux / truth) - 1) < 0.002
