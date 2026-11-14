"""Flats from the night sky and the illumination correction (plans/calibration.md CAL-11; IRAF mkskyflat /
mkillumflat): a dome or twilight flat can light the field differently from the dark sky by a few per cent, which
moves a star's brightness as it drifts across the frame.

    sky = super_sky(lights, offsets)        the median of the dithered lights, each divided by its own sky level,
                                            stars cut out — refused when the dithers are smaller than the stars
    illum = illumination(sky, flat)         the smooth large-scale ratio of the sky's response to the flat's
    corrected = flat * illum                a flat with the night sky's illumination and the flat's fine detail

The lights given are calibrated with the flat to be corrected or not flat-fielded at all; offsets are their
pointing shifts in pixels (from the alignment), used only to check the dithers.
"""

import numpy as np
from scipy import ndimage


def check_dithers(offsets, star_size_px):
    """None when the dithers are large enough (most pairs farther apart than a star's size), else the advice."""
    off = np.asarray(offsets, float).reshape(-1, 2)
    if len(off) < 5:
        return "at least five dithered frames are needed for a flat from the sky"
    d = np.hypot(*(off[:, None, :] - off[None, :, :]).transpose(2, 0, 1))
    apart = np.median(d[np.triu_indices(len(off), 1)])
    if apart < 2 * star_size_px:
        return (f"the frames moved by {apart:.0f} px, less than twice a star's size ({star_size_px:.0f} px): "
                "stars would print through")  # fmt: skip
    return None


def super_sky(lights, offsets=None, star_size_px=10.0, nsigma=3.0):
    """The night sky's flat (median 1) from dithered lights; ValueError with the advice when the dithers are too
    small."""
    lights = [np.asarray(f, float) for f in lights]
    if offsets is not None:
        advice = check_dithers(offsets, star_size_px)
        if advice:
            raise ValueError(advice)
    cube = []
    for f in lights:
        level = np.nanmedian(f[::4, ::4])
        noise = 1.4826 * np.nanmedian(np.abs(f[::4, ::4] - level))
        stars = ndimage.binary_dilation(f > level + nsigma * noise, iterations=int(max(2, star_size_px // 2)))
        cube.append(np.where(stars, np.nan, f / level))
    sky = np.nanmedian(np.array(cube), axis=0)
    sky = np.where(np.isfinite(sky), sky, np.nanmedian(sky))
    return sky / np.nanmedian(sky)


def illumination(sky, flat, smooth=31):
    """The smooth ratio sky / flat (normalised): what the flat gets wrong at large scale."""
    ratio = np.asarray(sky, float) / (np.asarray(flat, float) / np.nanmedian(flat))
    small = ndimage.median_filter(ratio[::4, ::4], size=max(3, smooth // 4), mode="nearest")
    big = ndimage.zoom(small, (ratio.shape[0] / small.shape[0], ratio.shape[1] / small.shape[1]), order=1)
    big = big[: ratio.shape[0], : ratio.shape[1]]
    big = ndimage.gaussian_filter(big, smooth / 4)
    return big / np.nanmedian(big)
