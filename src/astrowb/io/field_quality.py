"""Image quality across the field (plans/images.md IMG-4; what CCD Inspector and ASTAP's inspector report): every
star's size and shape from its second moments, and the field's FWHM described by a smooth surface — its tilt (the
plane: which side is softer, and by how much across the sensor) and its curvature (corners against the centre).

    q = analyse(data)       {"stars": n, "fwhm": median px, "tilt_percent", "tilt_angle" (deg), "curvature_percent",
                             "elongation", "angle" (deg, of the stars' long axes), "map": 2-D polynomial coefficients}
"""

import numpy as np

from ..photometry.fieldstars import detect_stars


def _shape(data, x, y, r):
    """(FWHM, elongation 1 − b/a, angle in degrees from +x) of a star from a 2-D Gaussian fitted within r px (moments
    of a cut-out are biased by its noise and its edge)."""
    from scipy.optimize import least_squares

    ix, iy = int(round(x)), int(round(y))
    cut = np.asarray(data[iy - r : iy + r + 1, ix - r : ix + r + 1], float)
    if cut.shape != (2 * r + 1, 2 * r + 1):
        return None
    yy, xx = np.mgrid[-r : r + 1, -r : r + 1]
    edge = np.concatenate([cut[0], cut[-1], cut[:, 0], cut[:, -1]])
    bg0 = float(np.median(edge))

    def model(p):
        amp, cx, cy, sa, sb, th, bg = p
        u = (xx - cx) * np.cos(th) + (yy - cy) * np.sin(th)
        v = -(xx - cx) * np.sin(th) + (yy - cy) * np.cos(th)
        return amp * np.exp(-(u**2 / (2 * sa**2) + v**2 / (2 * sb**2))) + bg

    start = [cut.max() - bg0, x - ix, y - iy, 1.2, 1.0, 0.0, bg0]
    try:
        limits = ([0, -3, -3, 0.3, 0.3, -np.pi, -np.inf], [np.inf, 3, 3, r, r, np.pi, np.inf])
        fit = least_squares(lambda p: (model(p) - cut).ravel(), start, bounds=limits)
    except ValueError:
        return None
    _, _, _, sa, sb, th, _ = fit.x
    if sb > sa:
        sa, sb, th = sb, sa, th + np.pi / 2
    return 2.3548 * np.sqrt(sa * sb), 1 - sb / sa, float(np.degrees(th) % 180)


def analyse(data, max_stars=400, r=8, saturation=None):
    data = np.asarray(data, float)
    ny, nx = data.shape
    xy = detect_stars(data, max_stars=max_stars, margin=r + 2, saturation=saturation)
    rows = []
    for x, y in xy:
        m = _shape(data, x, y, r)
        if m is not None and 0.5 < m[0] < 3 * r:
            rows.append((x, y, *m))
    if len(rows) < 10:
        raise ValueError("fewer than ten measurable stars on the frame")
    rows = np.array(rows)
    x, y, fwhm, elong, angle = rows.T
    u, v = (x - nx / 2) / (nx / 2), (y - ny / 2) / (ny / 2)  # −1 … 1 across the sensor
    design = np.column_stack([np.ones_like(u), u, v, u * u + v * v])
    keep = np.ones(len(u), bool)
    for _ in range(3):  # a blended pair or a galaxy does not bend the surface
        coef, *_ = np.linalg.lstsq(design[keep], fwhm[keep], rcond=None)
        res = fwhm - design @ coef
        s = 1.4826 * np.median(np.abs(res[keep]))
        keep = np.abs(res) < 3 * max(s, 1e-6)
    c0, cu, cv, cr = coef
    centre = c0
    tilt = np.hypot(cu, cv) * 2 / centre * 100  # from one edge to the other, per cent of the centre's FWHM
    corners = c0 + 2 * cr  # u² + v² = 2 at the corners
    doubled = np.radians(2 * angle)  # an axis, not a direction: averaged on the doubled angle
    mean_angle = float(np.degrees(0.5 * np.arctan2(np.median(np.sin(doubled)), np.median(np.cos(doubled)))) % 180)
    return {"stars": int(keep.sum()), "fwhm": float(np.median(fwhm[keep])), "tilt_percent": float(tilt),
            "tilt_angle": float(np.degrees(np.arctan2(cv, cu)) % 360),
            "curvature_percent": float((corners - centre) / centre * 100),
            "elongation": float(np.median(elong[keep])), "angle": mean_angle, "map": coef.tolist()}  # fmt: skip
