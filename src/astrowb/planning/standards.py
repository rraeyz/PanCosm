"""Standards for a target (plans/planning.md PLN-9): the stars of a standards list that stand at the target's
airmass close in time and on the sky, and a pair bracketing the night's airmass range for an extinction solution.

    rows = load("telluric")                                     the list (name, ra, dec, …) and its meta["comments"]
    best = matching(target, time, site, rows)                   [{name, airmass, target_airmass, separation, …}]
    low, high = extinction_pair(times, site, rows, (a0, a1))    a standard near each end of an airmass range
"""

from importlib.resources import files

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.table import Table
from astropy.time import Time

from .visibility import airmass, altitudes


def load(kind="telluric"):
    """A standards list as a Table; its source and selection are in meta["comments"]."""
    return Table.read(str(files("astrowb") / "resources" / "standards" / f"{kind}.ecsv"), format="ascii.ecsv")


def _coords(rows):
    return SkyCoord(np.asarray(rows["ra"], float) * u.deg, np.asarray(rows["dec"], float) * u.deg)


def matching(target, time, site, rows, tolerance=0.1, min_alt=20.0, limit=10):
    """The standards whose airmass at `time` is within `tolerance` of the target's, nearest on the sky first."""
    time = Time(time)
    stars = _coords(rows)
    alt_t = float(altitudes(target, time, site))
    alt = np.asarray(altitudes(stars, time, site), float)
    x_t, x = float(airmass(alt_t)), np.asarray(airmass(alt), float)
    sep = target.separation(stars).deg
    ok = (alt > min_alt) & (np.abs(x - x_t) <= tolerance)
    out = [
        dict(zip(rows.colnames, (rows[c][i] for c in rows.colnames), strict=True))
        | {"airmass": float(x[i]), "target_airmass": x_t, "separation": float(sep[i])}
        for i in np.flatnonzero(ok)
    ]
    return sorted(out, key=lambda r: r["separation"])[:limit]


def extinction_pair(times, site, rows, airmass_range, min_alt=20.0):
    """Two standards for an extinction solution: one seen at the low end of airmass_range and one at the high end
    during `times`, each with the time it gets there. None for an end no standard reaches within 0.1."""
    times = Time(times)
    stars = _coords(rows)
    alt = np.asarray(altitudes(stars[:, None], times[None, :], site), float)
    x = np.where(alt > min_alt, np.asarray(airmass(alt), float), np.inf)
    pair = []
    for goal in airmass_range:
        d = np.abs(x - goal)
        i, j = np.unravel_index(np.argmin(d), d.shape)
        pair.append(
            None if d[i, j] > 0.1 else {"name": str(rows["name"][i]), "time": times[j], "airmass": float(x[i, j])}
        )
    return tuple(pair)
