"""Satellite and aircraft trails (plans/calibration.md CAL-12): found, never repaired — the band is flagged so that
photometry can mark the points it touches (PHO-36).

A trail too faint to see on one pixel (2σ) stands out when the frame is summed along its line: the frame (sky
removed, stars cut out, binned 4 × 4) is projected on every direction (a Radon transform, Nir, Zackay & Ofek 2018
in spirit), the brightest line of mean flux per projected length wins, and its angle is refined around the peak.

    t = find(data)            {"angle" (deg, from +x), "offset" (px from the centre along the normal), "width",
                               "significance"} or None
    m = band(data.shape, t)   bool mask of the trail's pixels
"""

import numpy as np
from scipy import ndimage


def _projection(img, angles, nbins):
    """Mean of img along lines at each angle (deg), binned by their offset from the centre: (len(angles), nbins)
    means and counts."""
    ny, nx = img.shape
    yy, xx = np.indices(img.shape)
    x, y = (xx - (nx - 1) / 2).ravel(), (yy - (ny - 1) / 2).ravel()
    v = img.ravel()
    half = np.hypot(nx, ny) / 2
    out, counts = np.zeros((len(angles), nbins)), np.zeros((len(angles), nbins))
    for i, a in enumerate(np.radians(angles)):
        d = -x * np.sin(a) + y * np.cos(a)  # distance from the centre across a line at angle a
        k = np.clip(((d + half) / (2 * half) * nbins).astype(int), 0, nbins - 1)
        counts[i] = np.bincount(k, minlength=nbins)
        out[i] = np.bincount(k, weights=v, minlength=nbins)
    with np.errstate(invalid="ignore", divide="ignore"):
        return out / counts, counts, half


def _strongest(small, z_of, min_length):
    """(angle, offset index, z, nbins, half) of the line with the highest z, then refined in angle."""
    nbins = int(np.hypot(*small.shape))
    coarse = np.arange(0.0, 180.0, 0.5)
    means, counts, half = _projection(small, coarse, nbins)
    z = np.where(counts >= min_length * min(small.shape), z_of(means, counts), 0.0)
    i, _ = np.unravel_index(np.nanargmax(z), z.shape)
    fine = coarse[i] + np.arange(-0.6, 0.61, 0.05)
    m2, c2, _ = _projection(small, fine, nbins)
    z2 = np.where(c2 >= min_length * min(small.shape), z_of(m2, c2), 0.0)
    i2, j2 = np.unravel_index(np.nanargmax(z2), z2.shape)
    return float(fine[i2] % 180), j2, z2[i2], nbins, half


def find(data, nsigma=8.0, binning=4, min_length=0.3):
    """The strongest trail of the frame, or None when no line stands out by nsigma. Two looks: the faint one on the
    frame with its stars cut out and every pixel held within ±3σ, the bright one on the map of pixels above 5σ (a
    bright trail is cut out with the stars in the first)."""
    d = np.asarray(data, float)
    ny, nx = (s // binning * binning for s in d.shape)
    d = d[:ny, :nx]
    sky = np.nanmedian(d[::4, ::4])
    sigma = 1.4826 * np.nanmedian(np.abs(d[::4, ::4] - sky))
    bright = ndimage.binary_dilation(d - sky > 5 * sigma, iterations=2)
    clean = np.where(bright, 0.0, np.clip(d - sky, -3 * sigma, 3 * sigma))

    def binned(img):
        return img.reshape(ny // binning, binning, nx // binning, binning).mean(axis=(1, 3))

    noise = sigma / binning
    best = None
    faint = _strongest(binned(clean), lambda m, c: m / (noise / np.sqrt(np.maximum(c, 1))), min_length)
    # the bright look: the share of the line covered by bright pixels (a trail covers most of it, stars a few %)
    hard = _strongest(binned(bright.astype(float)), lambda m, c: m, min_length)
    for found, need in ((faint, nsigma), (hard, 0.3)):
        angle, j, z, nbins, half = found
        if z[j] >= need and (best is None or z[j] / need > best[2][best[1]] / best[5]):
            best = (angle, j, z, nbins, half, need)
    if best is None:
        return None
    angle, j, z, nbins, half, _ = best
    offset = ((j + 0.5) / nbins * 2 * half - half) * binning
    across = z[max(0, j - 5) : j + 6]
    width = max(1.0, float((across > z[j] / 2).sum()) * 2 * half / nbins * binning)
    return {"angle": angle, "offset": float(offset), "width": width, "significance": float(z[j])}


def band(shape, trail, margin=3.0):
    """bool mask of the pixels within width / 2 + margin of the trail's line."""
    ny, nx = shape
    yy, xx = np.indices(shape)
    a = np.radians(trail["angle"])
    d = -(xx - (nx - 1) / 2) * np.sin(a) + (yy - (ny - 1) / 2) * np.cos(a)
    return np.abs(d - trail["offset"]) <= trail["width"] / 2 + margin
