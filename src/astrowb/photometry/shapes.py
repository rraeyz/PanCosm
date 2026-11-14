"""Apertures that are not circles (plans/photometry.md PHO-22): an ellipse for a star stretched by tracking or
optics, a "racetrack" for a trailed star (two half circles joined by a rectangle along the trail), and painted
pixel masks (TESS-like stamps, blends).

    {"kind": "ellipse", "ratio": b/a, "angle": degrees from +x}     radii r_ap, r_in, r_out are the major semi-axes
    {"kind": "racetrack", "length": px, "angle": degrees from +x}   radii are distances from the trail's segment
    {"kind": "pixels", "mask": [bool 2-D per star]}                 the sky ring is r_in…r_out around each star

Each shape's sky ring has its own form (an elliptical ring, a ring of equal distance from the trail). The flux, its
error and the sky follow aperture.measure: a sigma-clipped median sky per pixel, the scatter in the ring, the same
error formula. Pixel overlaps are exact for the ellipse (photutils) and sampled 10 × 10 per pixel for the racetrack.
"""

import numpy as np
from astropy.stats import sigma_clip

SUB = 10  # samples per pixel side for the racetrack's overlap


def moments_shape(data, x, y, r):
    """(axis ratio b/a, angle in degrees from +x) of a star from the second moments of its light within r px."""
    half = int(np.ceil(r)) + 1
    y0, x0 = max(0, int(y) - half), max(0, int(x) - half)
    cut = np.asarray(data, float)[y0 : int(y) + half + 1, x0 : int(x) + half + 1]
    yy, xx = np.mgrid[y0 : y0 + cut.shape[0], x0 : x0 + cut.shape[1]]
    inside = np.hypot(xx - x, yy - y) <= r
    net = np.clip(cut - np.median(cut[~inside]) if (~inside).any() else cut, 0, None) * inside
    w = net / net.sum()
    dx, dy = xx - x, yy - y
    mxx, myy, mxy = (w * dx * dx).sum(), (w * dy * dy).sum(), (w * dx * dy).sum()
    common = np.hypot((mxx - myy) / 2, mxy)
    a2, b2 = (mxx + myy) / 2 + common, max((mxx + myy) / 2 - common, 1e-12)
    return float(np.sqrt(b2 / a2)), float(np.degrees(0.5 * np.arctan2(2 * mxy, mxx - myy)))


def _segment_distance(xx, yy, x, y, length, angle):
    """Distance of each point from the segment of the given length and angle centred on (x, y)."""
    ux, uy = np.cos(np.radians(angle)), np.sin(np.radians(angle))
    t = np.clip((xx - x) * ux + (yy - y) * uy, -length / 2, length / 2)
    return np.hypot(xx - (x + t * ux), yy - (y + t * uy))


def _racetrack(data, x, y, length, angle, r_ap, r_in, r_out):
    """(aperture sum, aperture area, ring pixel values) for one trailed star."""
    reach = int(np.ceil(length / 2 + r_out)) + 2
    ny, nx = data.shape
    ys, xs = slice(max(0, int(y) - reach), min(ny, int(y) + reach + 1)), slice(max(0, int(x) - reach),
                                                                               min(nx, int(x) + reach + 1))  # fmt: skip
    cut = data[ys, xs]
    yy, xx = np.mgrid[ys, xs]
    sub = (np.arange(SUB) + 0.5) / SUB - 0.5
    sx, sy = np.meshgrid(sub, sub)
    d_sub = _segment_distance(xx[..., None, None] + sx, yy[..., None, None] + sy, x, y, length, angle)
    weight = (d_sub <= r_ap).mean(axis=(-1, -2))
    d = _segment_distance(xx, yy, x, y, length, angle)  # the ring by pixel centres, as aperture.measure's
    return float((weight * cut).sum()), float(weight.sum()), cut[(d >= r_in) & (d <= r_out)]


def _ellipse(data, x, y, ratio, angle, r_ap, r_in, r_out):
    from photutils.aperture import EllipticalAnnulus, EllipticalAperture

    theta = np.radians(angle)
    ap = EllipticalAperture((x, y), a=r_ap, b=r_ap * ratio, theta=theta)
    an = EllipticalAnnulus((x, y), a_in=r_in, a_out=r_out, b_out=r_out * ratio, b_in=r_in * ratio, theta=theta)
    m = ap.to_mask(method="exact")
    total = float(np.nansum(m.multiply(data)))
    area = float(ap.area_overlap(data))
    ring = an.to_mask(method="center").get_values(data)
    return total, area, ring


def _pixels(data, x, y, mask, r_in, r_out):
    mask = np.asarray(mask, bool)
    yy, xx = np.indices(data.shape)
    d = np.hypot(xx - x, yy - y)
    return float(data[mask].sum()), float(mask.sum()), data[(d >= r_in) & (d <= r_out) & ~mask]


def measure_shaped(data, xy, shape, r_ap, r_in, r_out, gain=1.0):
    """aperture.measure for a shape: (flux, error, sky per pixel), one value per star."""
    data = np.asarray(data, float)
    out = []
    for i, (x, y) in enumerate(np.atleast_2d(np.asarray(xy, float))):
        kind = shape["kind"]
        if kind == "racetrack":
            total, area, ring = _racetrack(data, x, y, shape["length"], shape.get("angle", 0.0), r_ap, r_in, r_out)
        elif kind == "ellipse":
            total, area, ring = _ellipse(data, x, y, shape["ratio"], shape.get("angle", 0.0), r_ap, r_in, r_out)
        elif kind == "pixels":
            total, area, ring = _pixels(data, x, y, shape["mask"][i], r_in, r_out)
        else:
            raise ValueError(f"unknown aperture shape: {kind}")
        clipped = sigma_clip(ring[np.isfinite(ring)], sigma=3.0, maxiters=10)
        sky, noise, n_sky = float(np.ma.median(clipped)), float(np.ma.std(clipped)), int(clipped.count())
        flux = total - area * sky
        var = max(flux, 0.0) / gain + area * (1 + area / max(n_sky, 1)) * noise**2
        out.append((flux, np.sqrt(var), sky))
    flux, err, sky = (np.array(v) for v in zip(*out, strict=True))
    return flux, err, sky
