"""Pixels that spoil an aperture, found on the frame itself (plans/photometry.md PHO-36, the part that needs no mask
plane): "C" a one-pixel spike inside the aperture (cosmic ray, hot pixel): above its 3x3 median by 5 sigma (sky and
the star's photons) and by FINE times the fine structure a star has there (L.A.Cosmic's test, van Dokkum 2001), so
a sharp star's core is not one; "E" the aperture runs off the frame."""

import numpy as np

from .aperture import despike


def _spike(a, inside, sigma):
    """A pixel above the mean of its four neighbours by more than a star of the stamp's own core can be and by 5
    sigma (sky and photons, gain about 1). The star is a Gaussian of the stamp's own shape: the covariance of its
    second moments (elongation and angle) scaled to the narrower of two sizes, the half-maximum area of the
    median-filtered stamp or the moments' (a Moffat's sharp core). Its peak pixel, wherever the centre falls in it,
    is at most 1 - (exp(-Cxx / 2) + exp(-Cyy / 2)) / 2 of itself above the mean of its four neighbours (C the inverse
    covariance; 1.2 times C's diagonal kept as a margin). A round star of the mean width was assumed before: an
    elongated star of the owner's T100 night (58 % down on one side, 11 % on the other) was taken for a cosmic ray."""
    smooth = despike(np.clip(a, 0, None))[inside]  # the star without the spike
    if not smooth.size or smooth.max() <= 0:  # no pixel of the aperture in the stamp (a star off the frame's edge)
        return False
    area = np.count_nonzero(smooth >= smooth.max() / 2)  # the half-maximum area: a Moffat's sharp core
    w = np.clip(a, 0, None) * inside
    yy, xx = np.indices(a.shape)
    cx, cy = (w * xx).sum() / w.sum(), (w * yy).sum() / w.sum()
    dx, dy = xx - cx, yy - cy
    cov = np.array([[(w * dx * dx).sum(), (w * dx * dy).sum()], [(w * dx * dy).sum(), (w * dy * dy).sum()]]) / w.sum()
    size = np.sqrt(max(np.linalg.det(cov), 1e-6))  # the moments' s^2 (sx * sy), wings included
    s2 = max(min(4 * area / np.pi / 5.545, size), 0.25)  # the narrower: a core is never taken for a spike
    inv = np.linalg.inv(cov * s2 / size + 1e-9 * np.eye(2))
    drop = 1 - (np.exp(-0.5 * 1.2 * inv[0, 0]) + np.exp(-0.5 * 1.2 * inv[1, 1])) / 2
    p = np.pad(a, 1, mode="edge")
    lap = a - (p[:-2, 1:-1] + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:]) / 4
    noise = np.sqrt(sigma**2 + np.clip(a, 0, None))
    return bool(np.any(inside & (lap > np.clip(a, 0, None) * drop + 5 * noise)))


def aperture_flags(data, xy, r_ap):
    """One string per star: the letters of what spoils its aperture ("" when clean)."""
    data = np.asarray(data)  # the stamps are made float, not the frame: copying a 4k frame was 90 % of the time
    ny, nx = data.shape
    m = int(np.ceil(r_ap)) + 2
    out = []
    for x, y in np.asarray(xy, float).reshape(-1, 2):
        if not (np.isfinite(x) and np.isfinite(y)):  # no position on this frame
            out.append("E")
            continue
        flags = ""
        if x - r_ap < -0.5 or y - r_ap < -0.5 or x + r_ap > nx - 0.5 or y + r_ap > ny - 0.5:
            flags += "E"
        y0, y1, x0, x1 = max(int(y) - m, 0), min(int(y) + m + 1, ny), max(int(x) - m, 0), min(int(x) + m + 1, nx)
        if y1 <= y0 or x1 <= x0:  # off this frame (or the part of it that was read)
            out.append(flags or "E")
            continue
        stamp = np.asarray(data[y0:y1, x0:x1], float)
        if stamp.size >= 49 and np.isfinite(stamp).all():
            yy, xx = np.mgrid[y0:y1, x0:x1]
            inside = (xx - x) ** 2 + (yy - y) ** 2 <= r_ap * r_ap
            outer = stamp[~inside]
            if outer.size > 8:
                sky = np.median(outer)
                sigma = 1.4826 * np.median(np.abs(outer - sky))
                if _spike(stamp - sky, inside, sigma):
                    flags += "C"
        out.append(flags)
    return out
