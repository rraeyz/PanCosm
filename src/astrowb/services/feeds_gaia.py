"""Gaia Science Alerts as targets (plans/planning.md PLN-12): the public list of transients Gaia found (outbursts,
supernovae, microlensing events …) from the Cambridge alerts page, kept for a day (services.cache). Asked only when
the user presses for it in the Plan window; nothing is fetched otherwise.

    rows = alerts()                   [{name, ra, dec, mag, date, cls, comment}] newest first
    tonight = observable(rows, site, "2026-11-14", min_alt=30)   the ones above min_alt in tonight's dark hours
"""

import csv
import io
import urllib.request

import numpy as np

URL = "https://gsaweb.ast.cam.ac.uk/alerts/alerts.csv"
CREDIT = "Gaia Science Alerts (ESA / Gaia / DPAC, Cambridge)"


def parse(text):
    """The alerts CSV -> rows; lines without a position are left out."""
    lines = text.splitlines()
    if lines and lines[0].startswith("#"):
        lines[0] = lines[0][1:]
    out = []
    for r in csv.DictReader(io.StringIO("\n".join(lines)), skipinitialspace=True):
        try:
            ra, dec = float(r["RaDeg"]), float(r["DecDeg"])
        except (KeyError, TypeError, ValueError):
            continue
        mag = r.get("AlertMag") or ""
        out.append({"name": r["Name"], "ra": ra, "dec": dec, "mag": float(mag) if mag.strip() else None,
                    "date": r.get("Date", ""), "cls": r.get("Class", ""), "comment": r.get("Comment", "")})  # fmt: skip
    return out


def alerts(fetch=None):
    from .cache import cached

    def now():
        if fetch:
            return fetch(URL)
        with urllib.request.urlopen(URL, timeout=30) as r:  # noqa: S310 (a fixed https service)
            return r.read().decode("utf-8", "replace")

    return parse(cached("alerts", URL, now))


def observable(rows, site, date, min_alt=30.0):
    """The rows whose target is above min_alt during the dark hours (Sun below −12°) of the night beginning on date,
    each with its highest altitude then ("max_alt")."""
    from astropy.coordinates import SkyCoord

    from ..planning.visibility import altitudes, night_grid, sun_altitude

    if not rows:
        return []
    times = night_grid(site, date, 20.0)
    dark = sun_altitude(times, site) < -12
    if not dark.any():
        return []
    times = times[dark]
    stars = SkyCoord(np.array([r["ra"] for r in rows]), np.array([r["dec"] for r in rows]), unit="deg")
    alt = np.asarray(altitudes(stars[:, None], times[None, :], site), float).max(axis=1)
    return [r | {"max_alt": float(a)} for r, a in zip(rows, alt, strict=True) if a >= min_alt]
