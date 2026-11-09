"""PHO-32: a TESS-like stamp — mask, background, PLD against pointing jitter, and the centroid test of a blend."""

import numpy as np

from astrowb.photometry import pixels


def stamp(n=2000, jitter=0.25, seed=5, blend_depth=0.0, target_depth=0.0):
    """15 × 15 pixels; a bright target, a fainter neighbour 3 px away, a sky that drifts, the pointing jitters."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) * 2 / 1440  # 2-minute cadences
    dx = jitter * np.sin(2 * np.pi * t / 0.37) + rng.normal(0, 0.03, n)
    dy = jitter * np.cos(2 * np.pi * t / 0.53) + rng.normal(0, 0.03, n)
    sky = 50 + 30 * t
    yy, xx = np.indices((15, 15))
    transit = np.abs(t - t.mean()) < 0.06
    cube = np.zeros((n, 15, 15))
    for k in range(n):
        f_t = 2e4 * (1 - target_depth * transit[k])
        f_b = 4e3 * (1 - blend_depth * transit[k])
        for x0, y0, f in ((7.0, 7.0, f_t), (10.0, 7.0, f_b)):
            cube[k] += f / (2 * np.pi * 1.1**2) * np.exp(-((xx - x0 - dx[k]) ** 2 + (yy - y0 - dy[k]) ** 2) / 2.42)
        cube[k] += sky[k]
    cube += rng.normal(0, np.sqrt(cube))
    return t, cube, transit, sky


def test_mask_background_and_pld():
    t, cube, transit, sky = stamp(target_depth=0.01)
    mask = pixels.threshold_mask(cube, 3.0)
    assert mask[7, 7] and 20 < mask.sum() < 90 and not mask[0, 0] and not mask[14, 14]
    bkg = pixels.background(cube, mask)
    assert abs(np.mean(bkg - sky)) < 0.5 and np.std(bkg - sky) < 4  # the drifting sky followed
    tight = np.zeros_like(mask)
    tight[6:9, 6:9] = True  # a small aperture: the jitter moves light in and out of it
    flux = pixels.sap(cube, tight, bkg)
    out = ~transit
    flat = pixels.pld(cube, tight, flux, exclude=transit, bkg=bkg)
    raw_scatter = np.std(flux[out] / np.median(flux[out]))
    pld_scatter = np.std(flat[out] / np.median(flat[out]))
    photon = np.median(np.sqrt(np.clip(cube[:, tight], 0, None).sum(1))) / np.median(flux[out])
    assert pld_scatter < 0.8 * raw_scatter and pld_scatter < 1.15 * photon  # down to the photon noise
    depth = 1 - np.median(flat[transit]) / np.median(flat[out])
    assert 0.007 < depth < 0.0105  # kept (diluted a little by the neighbour's light in the mask)


def test_the_centroid_moves_when_the_neighbour_eclipses():
    t, cube, transit, _ = stamp(jitter=0.0, blend_depth=0.3)  # the neighbour eclipses, not the target
    mask = pixels.threshold_mask(cube, 3.0)
    bkg = pixels.background(cube, mask)
    shift = pixels.centroid_shift(cube, mask, transit, bkg)
    assert shift["significance"] > 5 and shift["dx"] < 0  # the light centre moves away from the eclipsing star
    _, quiet, transit2, _ = stamp(jitter=0.0, seed=6)
    own = pixels.threshold_mask(quiet, 3.0)
    none = pixels.centroid_shift(quiet, own, transit2, pixels.background(quiet, own))
    assert none["significance"] < 4
