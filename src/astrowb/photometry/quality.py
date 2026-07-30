"""Frame quality through a night: star size (FWHM), sky background and noise, the number of stars seen
(clouds, dew and haze lower it). Frames far worse than the night's typical frame are marked bad, so they
can be left out of photometry and stacks.

Typical = median over the night; a frame is bad when its FWHM is above fwhm_factor x the median, it shows
fewer than star_fraction x the median number of stars, or its background is above background_factor x the
median (twilight, Moon, clouds lit from below)."""

import numpy as np


def measure(path):
    from ..calibration.masters import load
    from ..devices.focus import hfr

    data, header = load(path)
    info = {}
    h, used = hfr(np.asarray(data, np.float32), info=info)
    return {
        "file": str(path),
        "fwhm": 2 * h if np.isfinite(h) else None,  # Gaussian star: FWHM = 2 x half-flux radius
        "stars": info.get("detected", 0),
        "background": info.get("background"),
        "noise": info.get("noise"),
        "date_obs": header.get("DATE-OBS"),
    }


def judge(rows, fwhm_factor=1.5, star_fraction=0.5, background_factor=3.0):
    """Adds "good" (bool) and "why" (list of reasons) to every row; returns the rows."""

    def median(key):
        values = [r[key] for r in rows if r[key] is not None]
        return float(np.median(values)) if values else None

    fwhm, stars, bkg = median("fwhm"), median("stars"), median("background")
    for r in rows:
        why = []
        if r["fwhm"] is None or not r["stars"]:
            why.append("no stars")
        elif fwhm and r["fwhm"] > fwhm_factor * fwhm:
            why.append("stars blurred")
        if stars and r["stars"] < star_fraction * stars and not why:  # blurred stars also hide faint ones
            why.append("few stars (clouds?)")
        if bkg and r["background"] is not None and r["background"] > background_factor * abs(bkg):
            why.append("bright sky")
        r["good"], r["why"] = not why, why
    return rows
