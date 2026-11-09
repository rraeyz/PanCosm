"""Light curves of moving objects (plans/photometry.md PHO-21): the aperture follows the object, every frame gets its
own zero point from the catalogue stars on it (fixed comparison stars do not work when the field drifts), frames
where the object passes a star are flagged, and the magnitudes are reduced to unit distances.

    pos = linear_track(times, (t1, x1, y1), (t2, x2, y2))     or positions from an ephemeris, refined by centroids
    rows = measure(frames, times, pos, stars, r_ap, r_in, r_out)   per frame: m, its error, zp, blended, …
    H = reduced(m, r_au, delta_au); jd_ltc = light_time(jd, delta_au)
"""

import numpy as np

from .aperture import measure as aperture_measure
from .aperture import recenter

C_AU_PER_DAY = 173.1446326846693


def linear_track(times, first, last):
    """(x, y) per time on the straight track between two (time, x, y) clicks."""
    (t1, x1, y1), (t2, x2, y2) = first, last
    f = (np.asarray(times, float) - t1) / (t2 - t1)
    return np.column_stack([x1 + f * (x2 - x1), y1 + f * (y2 - y1)])


def frame_zero_point(data, stars, r_ap, r_in, r_out, gain=1.0, clip=3.0):
    """(zero point, its error, stars used) of one frame from catalogue stars [(x, y, mag)] on it: the clipped,
    error-weighted mean of mag − m_inst."""
    xy = np.array([(x, y) for x, y, _ in stars], float)
    cat = np.array([m for *_, m in stars], float)
    flux, err, _ = aperture_measure(data, xy, r_ap, r_in, r_out, gain)
    ok = flux > 0
    zp = cat[ok] + 2.5 * np.log10(flux[ok])
    w = 1 / np.square(1.0857 * err[ok] / flux[ok])
    keep = np.ones(len(zp), bool)
    for _ in range(5):
        mean = np.average(zp[keep], weights=w[keep])
        scatter = np.sqrt(np.average((zp[keep] - mean) ** 2, weights=w[keep]))
        new = np.abs(zp - mean) <= clip * max(scatter, 1e-4)
        if np.array_equal(new, keep):
            break
        keep = new
    error = max(scatter / np.sqrt(keep.sum()), 1 / np.sqrt(w[keep].sum()))
    return float(mean), float(error), int(keep.sum())


def blended(xy, stars, obj_mag, r_out, brighter_by=4.0):
    """True when a catalogue star brighter than obj_mag + brighter_by is within r_out of the object."""
    for x, y, m in stars:
        if m < obj_mag + brighter_by and np.hypot(x - xy[0], y - xy[1]) < r_out:
            return True
    return False


def measure(frames, positions, stars, r_ap, r_in, r_out, gain=1.0, refine=True):
    """Per frame (frames: 2-D arrays; positions: the object's predicted (x, y); stars: per frame [(x, y, mag)] of
    catalogue stars on it, the object excluded): {"x", "y", "mag", "err", "zp", "zp_err", "n_stars", "blended"}."""
    rows = []
    for data, (x, y), field in zip(frames, positions, stars, strict=True):
        if refine:
            x, y = recenter(data, [(x, y)], max_move=3.0)[0]
        f, e, _ = aperture_measure(data, [(x, y)], r_ap, r_in, r_out, gain)
        zp, zp_err, n = frame_zero_point(data, field, r_ap, r_in, r_out, gain)
        m = zp - 2.5 * np.log10(f[0]) if f[0] > 0 else np.nan
        err = float(np.hypot(1.0857 * e[0] / f[0], zp_err)) if f[0] > 0 else np.nan
        rows.append({"x": float(x), "y": float(y), "mag": float(m), "err": err, "zp": zp, "zp_err": zp_err,
                     "n_stars": n, "blended": blended((x, y), field, m, r_out)})  # fmt: skip
    return rows


def reduced(mag, r_au, delta_au):
    """The magnitude at unit distances from the Sun and the observer: H(α) = m − 5 log10(r Δ)."""
    return np.asarray(mag, float) - 5 * np.log10(np.asarray(r_au, float) * np.asarray(delta_au, float))


def light_time(jd, delta_au):
    """The time the light left the object (JD − Δ/c), as ALCDEF's light-time correction asks."""
    return np.asarray(jd, float) - np.asarray(delta_au, float) / C_AU_PER_DAY
