"""The night of a site (plans/planning.md PLN-1): the almanac an observer reads first, the horizon profile that
every observability computation uses, and a month of nights to choose from.

    summary(site, "2026-11-14")      sunset, the dusks and dawns, sunrise, dark hours, the Moon's rise / set /
                                     illumination / highest point, the local sidereal time at dusk, midnight, dawn
    limit(horizon, az, min_alt)      the lowest usable altitude towards each azimuth (the profile, never below min_alt)
    parse_horizon(text)              a horizon file: "azimuth altitude" per line (N.I.N.A. / APT / Stellarium-style)
    month(site, "2026-11-01", 30)    per night: dark hours, the Moon's illumination and its hours up in the dark
"""

import astropy.units as u
import numpy as np

from .visibility import Site, moon, night_grid, sun_altitude


def parse_horizon(text):
    """[(azimuth, altitude)] sorted by azimuth from a two-column text (spaces, tabs, commas or semicolons; lines
    starting with # or ; and text lines are skipped)."""
    points = []
    for line in str(text).splitlines():
        line = line.strip()
        if not line or line[0] in "#;":
            continue
        parts = line.replace(",", " ").replace(";", " ").replace("\t", " ").split()
        try:
            az, alt = float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            continue  # a header line ("az alt")
        points.append((az % 360, alt))
    if len(points) < 2:
        raise ValueError("the horizon file has fewer than two azimuth-altitude pairs")
    return sorted(points)


def limit(horizon, az, min_alt=0.0):
    """The lowest usable altitude at the azimuths az: the profile (linear, wrapping at 360°) or min_alt."""
    az = np.asarray(az, float)
    if not horizon:
        return np.full(az.shape, float(min_alt))
    a, h = np.array(horizon, float).T
    return np.maximum(float(min_alt), np.interp(az % 360, a % 360, h, period=360))


def _crossing(hours, values, level, rising):
    v = np.asarray(values, float) - level
    for i in np.flatnonzero(np.sign(v[:-1]) != np.sign(v[1:])):
        if (v[i] < 0) == rising:
            return float(hours[i] + (hours[i + 1] - hours[i]) * v[i] / (v[i] - v[i + 1]))
    return None


def summary(site: Site, date: str, step_min=2.0):
    """The almanac of the night that begins on date (times as hours after 00:00 UTC of date; None when it does not
    happen that night — polar day or night)."""
    from astropy.time import Time

    times = night_grid(site, date, step_min)
    hours = (times.jd - Time(f"{date}T00:00:00").jd) * 24
    sun = sun_altitude(times, site)
    m = moon(times, site)
    out = {"date": date}
    for name, level in (("sun", -0.833), ("civil", -6.0), ("nautical", -12.0), ("astronomical", -18.0)):
        out[f"{name}_down"] = _crossing(hours, sun, level, rising=False)
        out[f"{name}_up"] = _crossing(hours, sun, level, rising=True)
    dark = sun < -18.0
    out["dark_hours"] = float(dark.sum() * step_min / 60)
    out["moon_rise"] = _crossing(hours, m["alt"], 0.125, rising=True)  # the Moon's centre at its apparent rise
    out["moon_set"] = _crossing(hours, m["alt"], 0.125, rising=False)
    k = int(np.argmax(m["alt"]))
    out["moon_highest"], out["moon_highest_alt"] = float(hours[k]), float(m["alt"][k])
    out["moon_illumination"] = (
        float(np.mean(m["illumination"][dark])) if dark.any() else float(np.mean(m["illumination"]))
    )
    out["moon_up_in_dark_hours"] = float((dark & (m["alt"] > 0)).sum() * step_min / 60)
    for name in ("astronomical_down", "astronomical_up"):
        h = out[name]
        out[f"lst_{name.split('_')[1]}"] = None if h is None else _lst(site, date, h)
    mid = 24.0 - site.lon / 15  # local midnight by the longitude, hours after 00:00 UTC of date
    out["lst_midnight"] = _lst(site, date, mid)
    return out


def _lst(site, date, hours):
    from astropy.time import Time

    t = Time(f"{date}T00:00:00") + hours / 24 * u.day
    return float(t.sidereal_time("mean", longitude=site.lon).hour)


def month(site: Site, start: str, nights=30):
    """[{date, dark_hours, moon_illumination, moon_up_in_dark_hours}] for nights from start."""
    from astropy.time import Time

    out = []
    for k in range(nights):
        date = (Time(f"{start}T12:00:00") + k * u.day).iso[:10]
        s = summary(site, date, step_min=10.0)
        out.append({key: s[key] for key in ("date", "dark_hours", "moon_illumination", "moon_up_in_dark_hours")})
    return out
