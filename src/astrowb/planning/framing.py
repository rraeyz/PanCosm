"""Where to point so that the target and the best comparison stars are on the sensor (plans/planning.md PLN-6).

    best = suggest(target, stars, fov=(w, h), margin=…)

target: (ra, dec) in degrees; stars: [(ra, dec, weight)] — the comparison stars that passed PHO-17's rules, weight
1 each or their rank's worth; fov: the sensor's width and height in arcminutes (from the equipment profile).
The pointing offset (in arcminutes, east and north of the target) and the rotation of the camera (when it can turn)
are searched on a grid; the one keeping the target and the most weight inside the frame, away from its edges by
`margin`, wins, the target nearer the middle breaking ties. Pure geometry on the tangent plane.
"""

import numpy as np


def _plane(ra, dec, ra0, dec0):
    """Gnomonic projection about (ra0, dec0) in arcminutes: x east, y north."""
    r, d, r0, d0 = (np.radians(np.asarray(v, float)) for v in (ra, dec, ra0, dec0))
    cosc = np.sin(d0) * np.sin(d) + np.cos(d0) * np.cos(d) * np.cos(r - r0)
    x = np.cos(d) * np.sin(r - r0) / cosc
    y = (np.cos(d0) * np.sin(d) - np.sin(d0) * np.cos(d) * np.cos(r - r0)) / cosc
    return np.degrees(x) * 60, np.degrees(y) * 60


def inside(x, y, centre, angle, fov, margin):
    """Which points (arcmin, tangent plane) fall in the frame centred at centre and turned by angle (deg)."""
    a = np.radians(angle)
    dx, dy = np.asarray(x) - centre[0], np.asarray(y) - centre[1]
    u = dx * np.cos(a) + dy * np.sin(a)
    v = -dx * np.sin(a) + dy * np.cos(a)
    return (np.abs(u) <= fov[0] / 2 - margin) & (np.abs(v) <= fov[1] / 2 - margin)


def suggest(target, stars, fov, margin=1.0, step=0.5, angles=(0.0,), target_margin=None):
    """{"offset": (east, north) arcmin, "angle", "kept": weight inside, "centred_kept": weight with the target in the
    middle at angle 0, "centre": (ra, dec) of the pointing}."""
    ra0, dec0 = target
    stars = np.asarray(stars, float).reshape(-1, 3)
    x, y = _plane(stars[:, 0], stars[:, 1], ra0, dec0)
    w = stars[:, 2]
    tm = margin if target_margin is None else target_margin
    reach = max(fov) / 2
    grid = np.arange(-reach, reach + step / 2, step)
    best = None
    for angle in angles:
        for cx in grid:
            for cy in grid:
                if not inside(0.0, 0.0, (cx, cy), angle, fov, tm):
                    continue  # the target itself must stay well inside
                kept = float(w[inside(x, y, (cx, cy), angle, fov, margin)].sum())
                key = (kept, -np.hypot(cx, cy))
                if best is None or key > best[0]:
                    best = (key, cx, cy, angle)
    if best is None:
        raise ValueError("the target cannot be kept inside the frame with these margins")
    (kept, _), cx, cy, angle = best
    centred = float(w[inside(x, y, (0.0, 0.0), 0.0, fov, margin)].sum())
    dra = cx / 60 / np.cos(np.radians(dec0))
    return {"offset": (float(cx), float(cy)), "angle": float(angle), "kept": kept, "centred_kept": centred,
            "centre": (float((ra0 + dra) % 360), float(dec0 + cy / 60))}  # fmt: skip


def _unplane(x, y, ra0, dec0):
    """The inverse of _plane: tangent-plane arcminutes back to (ra, dec) degrees."""
    xi, eta = np.radians(np.asarray(x, float) / 60), np.radians(np.asarray(y, float) / 60)
    d0 = np.radians(dec0)
    rho = np.hypot(xi, eta)
    c = np.arctan(rho)
    with np.errstate(invalid="ignore", divide="ignore"):
        dec = np.arcsin(np.cos(c) * np.sin(d0) + np.where(rho > 0, eta * np.sin(c) * np.cos(d0) / rho, 0.0))
    ra = ra0 + np.degrees(np.arctan2(xi * np.sin(c), rho * np.cos(d0) * np.cos(c) - eta * np.sin(d0) * np.sin(c)))
    return np.mod(ra, 360), np.degrees(dec)


def mosaic(centre, rows, cols, fov, overlap=0.15, angle=0.0):
    """Panels covering rows × cols frames of fov (arcmin) with the given overlap (share of a frame), the whole
    turned by angle: [{"row", "col", "ra", "dec", "angle"}]. Laid out on one tangent plane about the centre, so the
    rows stay straight near the pole; each panel's angle is turned by the plane's own north there (a camera at
    85° declination must turn panel by panel to keep the overlaps)."""
    ra0, dec0 = centre
    w, h = fov
    a = np.radians(angle)
    out = []
    for r in range(rows):
        for c in range(cols):
            u, v = (c - (cols - 1) / 2) * w * (1 - overlap), (r - (rows - 1) / 2) * h * (1 - overlap)
            x, y = u * np.cos(a) - v * np.sin(a), u * np.sin(a) + v * np.cos(a)
            ra, dec = _unplane(x, y, ra0, dec0)
            # the plane's "up" (turned by angle) at this panel, as a position angle on the sky
            ux, uy = -np.sin(a), np.cos(a)
            ra2, dec2 = _unplane(x + 0.01 * ux, y + 0.01 * uy, ra0, dec0)
            px, py = _plane(ra2, dec2, ra, dec)
            local = np.degrees(np.arctan2(-px, py))  # how far "up" is turned from local north (east positive)
            out.append({"row": r, "col": c, "ra": float(ra), "dec": float(dec), "angle": float(local)})
    return out
