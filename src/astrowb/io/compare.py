"""Is this new? (plans/images.md IMG-13): two frames of the same field — tonight's and an older one or a survey's —
aligned, brought to one flux scale, subtracted; what stands out in the difference is listed, and "what is this?"
names the catalogue objects near a position.

    d = difference(new, old)            {"image", "shift" (dx, dy), "scale"}
    found = new_sources(d["image"])     [(x, y, significance)] brighter in the new frame
    known = what_is((ra, dec), catalogue_rows, radius_arcsec)   the rows within the radius, nearest first
"""

import numpy as np
from scipy import ndimage


def _shift(a, b):
    """(dx, dy) that moves b onto a, from the peak of their cross-correlation (whole pixels, then the peak's
    parabola for the fraction)."""
    fa = np.fft.rfft2(a - np.median(a))
    fb = np.fft.rfft2(b - np.median(b))
    cc = np.fft.irfft2(fa * np.conj(fb), s=a.shape)
    iy, ix = np.unravel_index(np.argmax(cc), cc.shape)

    def sub(c, i, n, axis):
        m, p = cc.take((i - 1) % n, axis=axis), cc.take((i + 1) % n, axis=axis)
        lo, mid, hi = (np.take(m, c), np.take(cc.take(i, axis=axis), c), np.take(p, c))
        den = lo - 2 * mid + hi
        return 0.5 * (lo - hi) / den if den else 0.0

    dy = iy + sub(ix, iy, a.shape[0], 0)
    dx = ix + sub(iy, ix, a.shape[1], 1)
    dy = dy - a.shape[0] if dy > a.shape[0] / 2 else dy
    dx = dx - a.shape[1] if dx > a.shape[1] / 2 else dx
    return float(dx), float(dy)


def difference(new, old):
    """new − s · (old moved onto new) − its sky: s from the bright pixels' ratio after the skies are removed."""
    a, b = np.asarray(new, float), np.asarray(old, float)
    dx, dy = _shift(a, b)
    moved = ndimage.shift(b, (dy, dx), order=3, mode="nearest")
    sa, sb = np.median(a), np.median(moved)
    bright = (moved - sb) > 10 * 1.4826 * np.median(np.abs(moved - sb))
    scale = float(np.median((a - sa)[bright] / (moved - sb)[bright])) if bright.sum() > 20 else 1.0
    return {"image": (a - sa) - scale * (moved - sb), "shift": (dx, dy), "scale": scale}


def new_sources(diff, nsigma=8.0, smooth=1.5):
    """Positions (x, y, significance) of what is brighter in the new frame: the smoothed difference above nsigma."""
    d = ndimage.gaussian_filter(np.asarray(diff, float), smooth)
    noise = 1.4826 * np.median(np.abs(d - np.median(d)))
    labels, n = ndimage.label(d > nsigma * noise)
    out = []
    for k in range(1, n + 1):
        region = labels == k
        y, x = ndimage.center_of_mass(np.where(region, d, 0))
        out.append((float(x), float(y), float(d[region].max() / noise)))
    return sorted(out, key=lambda s: -s[2])


def what_is(position, rows, radius_arcsec=5.0):
    """The catalogue rows ({name, ra, dec, …}) within radius of position (ra, dec), nearest first, each with its
    distance in arcseconds."""
    ra, dec = position
    out = []
    for r in rows:
        d = 3600 * np.hypot((r["ra"] - ra) * np.cos(np.radians(dec)), r["dec"] - dec)
        if d <= radius_arcsec:
            out.append(dict(r) | {"distance_arcsec": float(d)})
    return sorted(out, key=lambda r: r["distance_arcsec"])
