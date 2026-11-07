"""Autofocus and meridian flips.

Autofocus: expose at focuser positions around the current one, measure the median half-flux
radius (HFR) of the stars in each frame, fit HFR(x) = sqrt(a (x - b)^2 + c) (a hyperbola: the
shape of a defocused star's size, Weber & Brady 2001), move to b. Refuses to move outside
the sampled range or when too few stars were measured.

Meridian flip: a German equatorial mount must change pier side after the target crosses the
meridian; the sequence re-slews to the same target once the hour angle exceeds flip_after
(the mount's own logic then flips) and restarts guiding.
"""

import time

import numpy as np
from astropy.coordinates import TETE
from astropy.stats import sigma_clipped_stats
from scipy.optimize import least_squares


def _hfr_one(data, med, x0, y0, r_max):
    from ..photometry.aperture import despike

    y_lo, y_hi = int(max(0, y0 - r_max - 1)), int(min(data.shape[0], y0 + r_max + 2))
    x_lo, x_hi = int(max(0, x0 - r_max - 1)), int(min(data.shape[1], x0 + r_max + 2))
    yy, xx = np.mgrid[y_lo:y_hi, x_lo:x_hi]
    r = np.hypot(xx - x0, yy - y0).ravel()
    flux = (despike(data[y_lo:y_hi, x_lo:x_hi]) - med).ravel()  # hot pixels and cosmic rays inside the star
    sel = r <= r_max
    order = np.argsort(r[sel])
    cum = np.cumsum(flux[sel][order])
    if cum[-1] <= 0:
        return np.nan
    return float(np.interp(cum[-1] / 2, cum, r[sel][order]))


def hfr(image, max_stars=50, info=None):
    """Median half-flux radius (pixels) of the brightest isolated stars, and how many were used.

    The measuring radius adapts to the star (3x the HFR, three passes) and stars with a detected
    neighbour inside that radius are skipped: neighbours would inflate the HFR.
    info (a dict) receives the number of stars detected, the sky background and its noise."""
    from photutils.detection import DAOStarFinder

    data = np.nan_to_num(np.asarray(image, dtype=np.float32))
    step = 4 if data.size > 4_000_000 else 2  # the sky from 360 000 pixels of a 2400 x 2400 frame: 0.15 -> 0.04 s
    _, med, std = sigma_clipped_stats(data[::step, ::step])
    if data.size > 4_000_000:  # find the stars on a 2x2-binned copy (4x faster); they are measured at full size
        ny, nx = (s // 2 * 2 for s in data.shape)
        binned = data[:ny, :nx].reshape(ny // 2, 2, nx // 2, 2).mean(axis=(1, 3))
        stars = DAOStarFinder(fwhm=2.0, threshold=4 * std, exclude_border=True)(binned - med)
        if stars is not None:
            for c in ("x_centroid", "y_centroid"):
                stars[c] = 2 * stars[c] + 0.5
    else:  # DAOStarFinder's sharpness limit already rejects single hot pixels
        stars = DAOStarFinder(fwhm=4.0, threshold=8 * std, exclude_border=True)(data - med)
    if info is not None:
        info |= {"detected": 0 if stars is None else len(stars), "background": float(med), "noise": float(std)}
    if stars is None or len(stars) == 0:
        return np.nan, 0
    stars.sort("flux", reverse=True)
    x, y = np.asarray(stars["x_centroid"]), np.asarray(stars["y_centroid"])
    r_max = 10.0
    radii = []
    for _ in range(3):
        radii = []
        for i in range(min(len(x), max_stars)):
            d = np.hypot(x - x[i], y - y[i])
            if np.sum(d < 2 * r_max) > 1:  # a neighbour would fall inside the measuring radius
                continue
            h = _hfr_one(data, med, x[i], y[i], r_max)
            if np.isfinite(h):
                radii.append(h)
        if not radii:
            return np.nan, 0
        r_max = max(4.0, 3 * float(np.median(radii)))
    return float(np.median(radii)), len(radii)


def fit_v_curve(positions, hfrs):
    """Best focus position from a hyperbolic fit; returns (best, fitted curve function)."""
    x, y = np.asarray(positions, float), np.asarray(hfrs, float)
    ok = np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 5:
        raise ValueError("too few focus measurements")
    i = int(np.argmin(y))
    scale = np.ptp(x) or 1.0
    xs = (x - x.mean()) / scale  # well-conditioned parameters

    def model(p, xx):
        return np.sqrt(np.clip(p[0] * (xx - p[1]) ** 2 + p[2], 1e-12, None))

    p0 = [max((y.max() ** 2 - y.min() ** 2) / max((xs.max() - xs[i]) ** 2, 1e-6), 1e-6), xs[i], y.min() ** 2]
    res = least_squares(lambda p: model(p, xs) - y, p0, bounds=([0, xs.min(), 0], [np.inf, xs.max(), np.inf]))
    best = res.x[1] * scale + x.mean()
    return float(best), (lambda xx: model(res.x, (np.asarray(xx, float) - x.mean()) / scale))


def autofocus(obs, exptime=2.0, step=50, n_steps=9, settle_s=0.2, expose=None):
    """Sweep the focuser around its current position, move to the fitted best. Returns a report dict."""
    from .sequence import Exposure
    from .sequence import expose as default_expose

    expose = expose or default_expose
    start = int(obs.call("focuser", "Position"))
    positions = start + step * (np.arange(n_steps) - n_steps // 2)
    hfrs, counts = [], []
    for p in positions:
        obs.call("focuser", "Move", int(p))
        while obs.call("focuser", "IsMoving"):
            time.sleep(settle_s)
        image, _ = expose(obs, Exposure(exptime, kind="light"))
        h, n = hfr(image)
        hfrs.append(h)
        counts.append(n)
    try:
        best, _ = fit_v_curve(positions, hfrs)
    except ValueError:
        obs.call("focuser", "Move", start)  # back where it was: never leave the focus worse
        raise
    best = int(round(best))
    obs.call("focuser", "Move", best)
    obs.note(f"autofocus: best position {best} (HFR {np.nanmin(hfrs):.2f} px)")
    return {"positions": positions.tolist(), "hfr": hfrs, "stars": counts, "best": best}


def hour_angle(obs, coord):
    """Hour angle (hours, -12..12) of coord now at the observatory."""
    t = obs.now()
    app = coord.transform_to(TETE(obstime=t, location=obs.location))
    lst = t.sidereal_time("apparent", longitude=obs.location.lon).hour
    return float((lst - app.ra.hour + 12) % 24 - 12)


def needs_flip(obs, coord, is_gem, flipped, flip_after_h=0.1):
    """True when a German mount should flip now: the target is past the meridian by flip_after_h and
    this target has not been flipped yet (a target first reached west of the meridian counts as flipped)."""
    return bool(is_gem and not flipped and hour_angle(obs, coord) > flip_after_h)
