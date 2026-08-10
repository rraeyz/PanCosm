"""Astrometry of a moving object (asteroid, comet) on plate-solved frames, and the MPC report.

The object is marked on the first and the last frame; on every frame its position is predicted from the
linear motion between them (in time) and re-centred, then turned into RA/Dec with that frame's WCS. Times
are mid-exposure UTC. A straight-line fit of the positions against time shows the residual of every
measurement (a star blended with the object, a bad solution).

The report is ADES PSV (the MPC's current format, version 2017): observatory code, people, telescope,
and one line per position.
"""

import numpy as np


def track(paths, first_xy, last_xy, box=11):
    """[{file, time (ISO UTC), x, y, ra, dec}] in time order; positions 0-based pixels."""
    from astropy.wcs import WCS

    from .. import timing
    from ..calibration.masters import load
    from .aperture import recenter

    paths = timing.chronological(paths)
    frames = [load(p) for p in paths]
    times = np.array([timing.mid_time(h).utc.jd for _, h in frames])
    span = times[-1] - times[0]
    rows = []
    for p, (data, header), t in zip(paths, frames, times, strict=True):
        wcs = WCS(header)
        if not wcs.has_celestial:
            raise ValueError("the image has no sky coordinates: plate-solve it first (Image menu)")
        f = (t - times[0]) / span if span > 0 else 0.0
        guess = np.asarray(first_xy, float) + f * (np.asarray(last_xy, float) - np.asarray(first_xy, float))
        x, y = recenter(data, [guess], box, max_move=box / 2)[0]
        sky = wcs.pixel_to_world(x, y)
        rows.append(
            {
                "file": str(p),
                "time": timing.Time(t, format="jd", scale="utc").isot,
                "x": float(x),
                "y": float(y),
                "ra": float(sky.ra.deg),
                "dec": float(sky.dec.deg),
                "ast_cat": header.get("ASTCAT"),  # the plate solution's star catalogue, when the solver said
            }
        )
    return residuals(rows)


def residuals(rows):
    """Adds "resid" (arcsec) from a straight-line motion fit; needs three positions."""
    if len(rows) < 3:
        return [r | {"resid": None} for r in rows]
    from astropy.time import Time

    t = Time([r["time"] for r in rows]).jd
    t = t - t.mean()
    dec = np.array([r["dec"] for r in rows])
    ra = np.unwrap(np.radians([r["ra"] for r in rows])) * np.degrees(1) * np.cos(np.radians(dec.mean()))
    d = []
    for v in (ra, dec):
        d.append(v - np.polyval(np.polyfit(t, v, 1), t))
    res = np.hypot(*d) * 3600
    return [r | {"resid": float(e)} for r, e in zip(rows, res, strict=True)]


def ades_psv(rows, designation, mpc_code, observers, measurers=None, telescope=None, ast_cat="Gaia3"):
    """ADES PSV text. designation: provisional (e.g. '2024 AB1'), permanent number, or a temporary name."""
    if not designation or not mpc_code or not observers:
        raise ValueError("designation, observatory code and observer names are required")
    is_number = str(designation).isdigit()
    lines = ["# version=2017", "# observatory", f"! mpcCode {mpc_code}"]
    lines += ["# submitter", f"! name {observers[0]}", "# observers"] + [f"! name {n}" for n in observers]
    lines += ["# measurers"] + [f"! name {n}" for n in (measurers or observers)]
    tel = telescope or {}
    lines += ["# telescope", f"! design {tel.get('design', 'reflector')}", f"! aperture {tel.get('aperture', 0.3)}"]
    lines += ["! detector CCD"]
    lines.append("permID|provID|trkSub|mode|stn|obsTime|ra|dec|astCat")
    for r in rows:
        perm, prov, trk = (designation, "", "") if is_number else ("", designation, "")
        if not is_number and not any(ch.isdigit() for ch in str(designation)[:4]):
            prov, trk = "", designation  # an object without a designation yet: tracklet name
        t = r["time"]
        t = (t if "." in t else t + ".000")[:23] + "Z"
        lines.append(f"{perm}|{prov}|{trk}|CCD|{mpc_code}|{t}|{r['ra']:.6f}|{r['dec']:+.6f}|{ast_cat}")
    return "\n".join(lines) + "\n"
