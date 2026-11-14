"""Fringe correction for thinned CCDs in red and narrow bands (plans/calibration.md CAL-10; IRAF mkfringecor and
ccdproc's fringecor, Snodgrass & Carry 2013).

    fringe = make_fringe_frame(lights)      the fringes in units of the sky: the dithered frames, stars cut out,
                                            each over its sky, median-combined, the smooth background removed
    a = fit_amplitude(light, fringe)        least squares on the pixels without stars: light ≈ sky·(1 + a·fringe)
    corrected = remove(light, fringe)       light − a · sky · fringe
"""

import numpy as np
from scipy import ndimage


def _stars(img, nsigma=2.0, grow=3):
    level = np.nanmedian(img[::4, ::4])
    noise = 1.4826 * np.nanmedian(np.abs(img[::4, ::4] - level))
    return ndimage.binary_dilation(img > level + nsigma * 2 * noise, iterations=grow), level, noise


def make_fringe_frame(lights, smooth=61, sigma=1.5):
    """The fringe pattern (mean 0, units of the sky level) from five or more dithered frames of one filter."""
    lights = [np.asarray(f, float) for f in lights]
    if len(lights) < 5:
        raise ValueError("at least five dithered frames of the filter are needed for a fringe frame")
    cube = []
    for f in lights:
        mask, level, _ = _stars(f)
        cube.append(np.where(mask, np.nan, f / level - 1.0))
    pattern = np.nanmedian(np.array(cube), axis=0)
    pattern = np.where(np.isfinite(pattern), pattern, 0.0)
    smooth_part = ndimage.median_filter(pattern, size=smooth, mode="nearest")
    # a little smoothing: a noisy fringe frame would bias the fitted amplitude low (noise in the regressor) and
    # add its noise to every light; what it takes of the fringes is taken alike in the fit and the subtraction
    return ndimage.gaussian_filter(pattern - smooth_part, sigma).astype(np.float32)


def fit_amplitude(light, fringe):
    """The fringes' amplitude in this frame (1: as strong as in the fringe frame), least squares on star-free pixels
    after the light's smooth background is removed."""
    f = np.asarray(light, float)
    mask, level, _ = _stars(f)
    rel = f / level - 1.0
    rel = rel - ndimage.median_filter(np.where(mask, 0.0, rel), size=61, mode="nearest")
    use = ~mask & np.isfinite(rel)
    fr = np.asarray(fringe, float)[use]
    return float(np.sum(rel[use] * fr) / np.sum(fr * fr))


def remove(light, fringe, amplitude=None):
    """The light with its fringes taken away (the amplitude fitted when not given)."""
    f = np.asarray(light, float)
    a = fit_amplitude(f, fringe) if amplitude is None else amplitude
    level = np.nanmedian(f[::4, ::4])
    return (f - a * level * np.asarray(fringe, float)).astype(np.float32)
