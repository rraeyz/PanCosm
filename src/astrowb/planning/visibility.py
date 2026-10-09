"""Night planning: twilight, altitude / airmass curves, Moon, and eclipse / transit events.

Pure astropy (AltAz, get_body with the built-in ephemeris): works offline. The Sun and Moon
are sampled on a fine time grid and twilight crossings are interpolated (accuracy ~10 s,
far below what planning needs). Airmass: core/units.airmass, Young (1994) from the true altitude, as in
Photometry and Observing (ARC-15 item 6); finite down to the horizon.
"""

from dataclasses import dataclass

import astropy.units as u
import numpy as np
from astropy.coordinates import AltAz, EarthLocation, SkyCoord, get_body
from astropy.time import Time

from .. import timing  # noqa: F401  (sets offline IERS behaviour)

TWILIGHT = {"civil": -6.0, "nautical": -12.0, "astronomical": -18.0}


@dataclass
class Site:
    name: str
    lat: float  # deg, north positive
    lon: float  # deg, east positive
    height: float = 0.0  # m

    @property
    def location(self):
        return EarthLocation.from_geodetic(self.lon * u.deg, self.lat * u.deg, self.height * u.m)


def airmass(alt_deg):
    """Airmass of true altitudes (core/units.airmass, Young 1994); NaN below the horizon."""
    from ..core.units import airmass as of_altitude

    return np.asarray(of_altitude(np.asarray(alt_deg, float)))


def night_grid(site: Site, date: str, step_min=5.0):
    """Times from local noon of `date` to local noon the next day (local = by longitude)."""
    noon = Time(f"{date}T12:00:00") - site.lon / 360 * u.day
    return noon + np.arange(0, 24 * 60 + step_min, step_min) * u.min


def altitudes(coord: SkyCoord, times: Time, site: Site):
    frame = AltAz(obstime=times, location=site.location)
    return coord.transform_to(frame).alt.deg


def sun_altitude(times, site):
    return get_body("sun", times, site.location).transform_to(AltAz(obstime=times, location=site.location)).alt.deg


def _crossings(times, values, level):
    """Times where values cross level (linear interpolation): (falling, rising)."""
    v = np.asarray(values) - level
    out = {"down": [], "up": []}
    for i in np.nonzero(np.sign(v[:-1]) != np.sign(v[1:]))[0]:
        f = v[i] / (v[i] - v[i + 1])
        t = times[i] + f * (times[i + 1] - times[i])
        out["down" if v[i] > 0 else "up"].append(t)
    return out


def night(site: Site, date: str, kind="astronomical"):
    """(dusk, dawn) of the night starting on `date`; None where the Sun never gets that low/high."""
    t = night_grid(site, date, 2.0)
    c = _crossings(t, sun_altitude(t, site), TWILIGHT[kind])
    return (c["down"][0] if c["down"] else None), (c["up"][0] if c["up"] else None)


def moon(times, site, coord=None):
    """Moon altitude, illuminated fraction, and separation from coord (deg) if given."""
    loc = site.location
    m = get_body("moon", times, loc)
    s = get_body("sun", times, loc)
    elong = s.separation(m)
    phase = np.arctan2(s.distance * np.sin(elong), m.distance - s.distance * np.cos(elong))
    out = {
        "alt": m.transform_to(AltAz(obstime=times, location=loc)).alt.deg,
        "illumination": np.asarray((1 + np.cos(phase)) / 2),
    }
    if coord is not None:
        out["separation"] = m.separation(coord.transform_to(m)).deg  # in the Moon's (geocentric) frame
    return out


@dataclass
class Event:
    kind: str  # "primary" (minimum I or transit) | "secondary"
    mid: Time
    start: Time | None
    end: Time | None
    alt_mid: float
    fully_observable: bool  # start..end in the dark with altitude >= min_alt


def events(t0_bjd, period, coord, site, dusk, dawn, duration_d=None, secondary=False, min_alt=20.0):
    """Minima/transits with mid-time between dusk and dawn.

    t0_bjd is BJD_TDB; for planning, the barycentric correction (<= 8.3 min) is applied back
    to UTC so the predicted times are wall-clock times."""
    if dusk is None or dawn is None:
        return []
    corr = timing.bjd_tdb(dusk, coord, site.location).jd - dusk.utc.jd  # BJD_TDB - JD_UTC near this night
    lo = dusk.utc.jd + corr
    hi = dawn.utc.jd + corr
    phases = [(0.0, "primary")] + ([(0.5, "secondary")] if secondary else [])
    out = []
    for shift, kind in phases:
        n0 = np.ceil((lo - t0_bjd) / period - shift)
        for n in np.arange(n0, n0 + 1 + (hi - lo) / period):
            mid_bjd = t0_bjd + (n + shift) * period
            if not lo <= mid_bjd <= hi:
                continue
            mid = Time(mid_bjd - corr, format="jd", scale="utc")
            half = (duration_d or 0) / 2
            start = mid - half * u.day if duration_d else None
            end = mid + half * u.day if duration_d else None
            check = Time([start or mid, mid, end or mid])
            alt = altitudes(coord, check, site)
            full = bool(np.all(alt >= min_alt) and check[0] >= dusk and check[-1] <= dawn)
            out.append(Event(kind, mid, start, end, float(alt[1]), full))
    return sorted(out, key=lambda e: e.mid.jd)
