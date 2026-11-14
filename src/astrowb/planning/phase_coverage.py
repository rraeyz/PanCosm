"""Which phases of a periodic star are still missing, and on which nights they can be observed (plans/planning.md
PLN-8).

    have = covered(times, t0, period, bins=50)        the phases the user's data already hold (bool per bin)
    plan = windows(site, start, nights, coord, t0, period, have, min_alt)
        [{"date", "start", "end" (JD UTC), "phases" (from, to), "new" (share of missing bins it covers)}] best first
    weeks = commensurability(period)                  how long until the phases visible at night drift round once

A period near a whole number of days (1.0003 d) shows nearly the same phases night after night: the planner says
how many weeks the gaps take to close.
"""

import astropy.units as u
import numpy as np

from .visibility import Site, altitudes, night_grid, sun_altitude


def phases(times, t0, period):
    return np.mod((np.asarray(times, float) - t0) / period, 1.0)


def covered(times, t0, period, bins=50):
    """bool per phase bin: does the data hold a point there?"""
    have = np.zeros(bins, bool)
    have[(phases(times, t0, period) * bins).astype(int) % bins] = True
    return have


def commensurability(period, nights_per_week=7):
    """Weeks until the phase observed at the same clock time has moved through a whole cycle (inf for a period of
    exactly a whole number of days or its fraction)."""
    ratio = 1.0 / period  # cycles per day
    drift = abs(ratio - round(ratio))  # phase change from one night to the next at the same time
    return np.inf if drift < 1e-9 else 1.0 / drift / nights_per_week


def windows(site: Site, start, nights, coord, t0, period, have, min_alt=30.0, step_min=10.0, sun_limit=-12.0):
    """The dark, high-enough stretches of each night, each with the share of the missing phase bins it would
    cover; best first. coord: the target's SkyCoord."""
    from astropy.time import Time

    bins = len(have)
    missing = ~np.asarray(have, bool)
    out = []
    for k in range(nights):
        date = (Time(f"{start}T12:00:00") + k * u.day).iso[:10]
        t = night_grid(Site(site.name, site.lat, site.lon, site.height), date, step_min)
        ok = (sun_altitude(t, site) < sun_limit) & (altitudes(coord, t, site) >= min_alt)
        if not ok.any():
            continue
        edges = np.flatnonzero(np.diff(np.r_[0, ok.astype(int), 0]))
        for a, b in zip(edges[0::2], edges[1::2], strict=True):  # each usable stretch of the night
            jd = t.jd[a:b]
            hit = np.zeros(bins, bool)
            hit[(phases(jd, t0, period) * bins).astype(int) % bins] = True
            new = float((hit & missing).sum() / max(missing.sum(), 1))
            if new > 0:
                ph = phases(jd[[0, -1]], t0, period)
                out.append({"date": date, "start": float(jd[0]), "end": float(jd[-1]),
                            "phases": (float(ph[0]), float(ph[1])), "new": new})  # fmt: skip
    out.sort(key=lambda w: (-w["new"], w["start"]))
    return out
