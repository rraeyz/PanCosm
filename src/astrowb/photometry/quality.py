"""Frame quality through a night: star size (FWHM), sky background and noise, the number of stars seen
(clouds, dew and haze lower it). Frames far worse than the night's typical frame are marked bad, so they
can be left out of photometry and stacks.

Typical = median over the night; a frame is bad when its FWHM is above fwhm_factor x the median, it shows
fewer than star_fraction x the median number of stars, or its background is above background_factor x the
median (twilight, Moon, clouds lit from below)."""

import numpy as np


def measure_run(paths):
    """measure() of consecutive frames, and the shift between each pair while the frame is open (fpack
    decompression is half a frame's time; the comparison suggestion and the light curve then find the shifts kept
    instead of opening every frame again). Returns (rows, binning, shifts)."""
    from ..calibration.masters import load
    from .aperture import frame_shift

    rows, shifts, prev, binning = [], [], None, 1
    for p in paths:
        data, header = load(p)
        binning = 2 if data.size > 4e6 else 1  # as the light curve and the suggestion take them
        if prev is not None:
            shifts.append(frame_shift(prev, data, binning))
        rows.append(measure(p, (data, header)))
        prev = data
    return rows, binning, shifts


def measure(path, loaded=None):
    from ..calibration.masters import load
    from ..devices.focus import hfr

    data, header = loaded if loaded is not None else load(path)
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


def _running_upper(y, half=10):
    """A running upper envelope: the 90th percentile within ± half frames."""
    y = np.asarray(y, float)
    return np.array([np.nanpercentile(y[max(0, i - half) : i + half + 1], 90) for i in range(len(y))])


def night_flags(ensemble=None, fwhm=None, x=None, y=None, peak=None, linearity=None, cloud_drop=0.2,
                seeing_factor=1.5, jump_px=5.0, near_saturation=0.9):  # fmt: skip
    """PHO-33: flags per frame from the night's series (any can be missing): "cloud" (the comparison stars' summed
    counts more than cloud_drop below their running upper envelope), "seeing" (FWHM above seeing_factor × the
    median), "jump" (the field moved by more than jump_px since the previous frame: a meridian flip or lost
    guiding), "near_saturation" (the target's peak above near_saturation × the linearity limit).
    Returns {kind: frame indices} and the one-line verdict."""
    flags = {}
    if ensemble is not None:
        e = np.asarray(ensemble, float)
        flags["cloud"] = np.flatnonzero(e < (1 - cloud_drop) * _running_upper(e)).tolist()
    if fwhm is not None:
        f = np.asarray(fwhm, float)
        flags["seeing"] = np.flatnonzero(f > seeing_factor * np.nanmedian(f)).tolist()
    if x is not None and y is not None:
        step = np.hypot(np.diff(np.asarray(x, float)), np.diff(np.asarray(y, float)))
        flags["jump"] = (np.flatnonzero(step > jump_px) + 1).tolist()
    if peak is not None and linearity:
        flags["near_saturation"] = np.flatnonzero(np.asarray(peak, float) > near_saturation * linearity).tolist()
    words = {"cloud": "behind cloud", "seeing": "with bad seeing", "jump": "after a jump of the field",
             "near_saturation": "near saturation"}  # fmt: skip
    verdict = "; ".join(f"{len(v)} frames {words[k]}" for k, v in flags.items() if v) or "no frame flagged"
    return flags, verdict


def lc_checks(lc):
    """night_flags from a measured light curve (photometry.lightcurve's dict): the comparison stars' summed counts,
    the FWHM, the target's position and its peak against the saturation level."""
    comp = np.asarray(lc.get("comp_flux", []), float)
    ensemble = np.nansum(comp.reshape(len(comp), -1), axis=1) if comp.size else None
    xy = lc.get("xy") or []
    x = [r[0][0] for r in xy] if xy else None
    y = [r[0][1] for r in xy] if xy else None
    peak = [p[0] for p in lc["peak"]] if lc.get("peak") else None
    flags, verdict = night_flags(ensemble, lc.get("fwhm"), x, y, peak, lc.get("saturation"))
    n_comp = comp.reshape(len(comp), -1).shape[1] if comp.size else 0
    spoiled = [i for i, r in enumerate(lc.get("flags") or []) if "C" in "".join(r[: 1 + n_comp])]  # PHO-36
    if spoiled:  # a cosmic ray or hot pixel in the target's or a comparison star's aperture
        flags["spike"] = spoiled
        verdict = (f"{len(spoiled)} frames with a spike in an aperture; " + verdict).replace("; no frame flagged", "")
    return flags, verdict
