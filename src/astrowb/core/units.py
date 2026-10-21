"""Named conversions used everywhere (plans/architecture.md ARC-15). No Qt here.

convert_times(values, standard, target, site): Julian dates given in one standard (JD_UTC, MJD_UTC, HJD_UTC,
BJD_TDB, …) for a target and a site, in every standard, with altitude, azimuth, hour angle and airmass.

vac_to_air / air_to_vac: wavelengths in Angstrom (Morton 2000, ApJS 130, 403, the IAU standard; above 2000 A).
flux_to_mag / mag_to_flux: with the error carried when one is given.

airmass(altitude, formula): the air mass of a line of sight at a true (geometric) altitude in degrees. Young (1994)
is the default; sec z is 3 % too large at 10° and grows without limit towards the horizon. The formula's name is
written beside every airmass column (AIRMASS_NOTE).
"""

import numpy as np

AIRMASS_FORMULAS = ("young1994", "secz", "hardie1962", "kastenyoung1989", "pickering2002")
AIRMASS_NOTE = {
    "young1994": "Young (1994, Appl. Opt. 33, 1108)",
    "secz": "sec z (plane-parallel)",
    "hardie1962": "Hardie (1962)",
    "kastenyoung1989": "Kasten & Young (1989, Appl. Opt. 28, 4735)",
    "pickering2002": "Pickering (2002, DIO 12, 3)",
}


def airmass(altitude_deg, formula="young1994"):
    """Air mass at the true altitude (degrees, scalar or array); NaN at or below the horizon."""
    h = np.asarray(altitude_deg, float)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        z = np.radians(90.0 - h)
        c = np.cos(z)
        if formula == "young1994":
            x = (1.002432 * c**2 + 0.148386 * c + 0.0096467) / (c**3 + 0.149864 * c**2 + 0.0102963 * c + 0.000303978)
        elif formula == "secz":
            x = 1.0 / c
        elif formula == "hardie1962":
            s = 1.0 / c - 1.0
            x = 1.0 / c - 0.0018167 * s - 0.002875 * s**2 - 0.0008083 * s**3
        elif formula == "kastenyoung1989":
            x = 1.0 / (c + 0.50572 * (96.07995 - (90.0 - h)) ** -1.6364)
        elif formula == "pickering2002":
            x = 1.0 / np.sin(np.radians(h + 244.0 / (165.0 + 47.0 * np.abs(h) ** 1.1)))
        else:
            raise ValueError(f"unknown airmass formula {formula}")
        x = np.where(h > 0, x, np.nan)
    return float(x) if np.ndim(x) == 0 else x


STANDARDS = ("JD_UTC", "MJD_UTC", "JD_TT", "HJD_UTC", "HJD_TT", "BJD_UTC", "BJD_TDB")
DIRECT_ABOVE = 2000  # more times than this: light times on a grid and interpolated (Astropy takes 0.3 ms a time)


def _light_time(t, target, how):
    """Light travel time (TimeDelta) to the barycentre or the Sun at times t. Many times: computed every 0.02 d
    (and at least every span / 20 000) and interpolated linearly: the error stays below 0.1 ms at a site (the daily
    21 ms term) and far below over the Earth's orbit."""
    from astropy.time import Time, TimeDelta

    if t.size <= DIRECT_ABOVE:
        return t.light_travel_time(target, kind=how, ephemeris="builtin")
    jd = t.jd
    step = max(0.02, (jd.max() - jd.min()) / 20000)
    nodes = np.arange(jd.min(), jd.max() + step, step)
    grid = Time(nodes, format="jd", scale=t.scale, location=t.location)
    seconds = grid.light_travel_time(target, kind=how, ephemeris="builtin").to_value("s")
    return TimeDelta(np.interp(jd, nodes, seconds), format="sec")


def convert_times(values, standard, target, site=None):
    """{standard: array} for every STANDARDS entry, plus "alt", "az" (deg), "ha" (h), "airmass" (when a site is
    given). values: Julian dates (or MJD for MJD_UTC) in `standard`; target: SkyCoord; site: EarthLocation or None
    (geocentre: no altitude). Heliocentric and barycentric dates are turned back into UTC iteratively (the light
    travel time depends on the time itself; two passes reach microseconds)."""
    import astropy.units as u
    from astropy.coordinates import AltAz, EarthLocation
    from astropy.time import Time

    if standard not in STANDARDS:
        known = ", ".join(STANDARDS)
        raise ValueError(f"unknown time standard {standard}; known: {known}")
    where = site if site is not None else EarthLocation.from_geocentric(0, 0, 0, unit=u.m)
    v = np.atleast_1d(np.asarray(values, float))
    kind, scale = standard.split("_")
    base = Time(v, format="mjd" if kind == "MJD" else "jd", scale=scale.lower(), location=where)
    if kind in ("HJD", "BJD"):
        how = "heliocentric" if kind == "HJD" else "barycentric"
        t = base
        for _ in range(3):  # t + light time(t) = given: solve for t
            t = Time(base - _light_time(t, target, how), location=where)
        base = t
    utc = base.utc
    bary = _light_time(utc, target, "barycentric")
    helio = _light_time(utc, target, "heliocentric")
    out = {
        "JD_UTC": utc.jd,
        "MJD_UTC": utc.mjd,
        "JD_TT": utc.tt.jd,
        "HJD_UTC": (utc + helio).utc.jd,
        "HJD_TT": (utc.tt + helio).jd,
        "BJD_UTC": (utc + bary).utc.jd,
        "BJD_TDB": (utc.tdb + bary).jd,
    }
    if site is not None and utc.size <= DIRECT_ABOVE:  # shortcut: no altitudes for long batches (40 s per 10^5)
        frame = AltAz(obstime=utc, location=site)
        altaz = target.transform_to(frame)
        lst = utc.sidereal_time("apparent", longitude=site.lon)
        out["alt"], out["az"] = altaz.alt.deg, altaz.az.deg
        out["ha"] = ((lst - target.ra).wrap_at(12 * u.hourangle)).hour
        out["airmass"] = np.atleast_1d(airmass(out["alt"]))
        out["v_bary"] = np.atleast_1d(velocity_correction(utc, target, site))
    return out


SOLAR_MOTION = (11.1, 12.24, 7.25)  # km/s towards the Galactic centre, rotation, north pole (Schönrich+ 2010)
FRAMES = ("barycentric", "heliocentric", "lsr")


def velocity_correction(time, target, site, frame="barycentric"):
    """km/s to add to a velocity observed at site and time (astropy Time) to have it in frame (ARC-15 item 1):
    the barycentre or the Sun (astropy's radial_velocity_correction), or the local standard of rest (barycentric
    plus the Sun's motion relative to it, Schönrich, Binney & Dehnen 2010, projected on the line of sight)."""
    if frame not in FRAMES:
        raise ValueError(f"unknown velocity frame {frame}; known: {', '.join(FRAMES)}")
    from astropy.time import Time

    kind = "heliocentric" if frame == "heliocentric" else "barycentric"
    time = Time(time.jd1, time.jd2, format="jd", scale=time.scale)  # astropy refuses a site given twice
    v = target.radial_velocity_correction(kind=kind, obstime=time, location=site).to_value("km/s")
    if frame == "lsr":
        g = target.galactic.cartesian.xyz.value  # unit vector: x to the centre, y along rotation, z to the pole
        v = v + float(np.dot(SOLAR_MOTION, g / np.linalg.norm(g)))
    return v


def vac_to_air(w):
    """Air wavelength (Angstrom) of a vacuum wavelength (Morton 2000; valid above 2000 A)."""
    w = np.asarray(w, float)
    s2 = (1e4 / w) ** 2
    return w / (1 + 8.34254e-5 + 2.406147e-2 / (130 - s2) + 1.5998e-4 / (38.9 - s2))


def air_to_vac(w):
    """Vacuum wavelength (Angstrom) of an air wavelength: vac_to_air inverted (three passes reach 1e-8 A)."""
    air = np.asarray(w, float)
    vac = air.copy()
    for _ in range(3):
        vac = vac + (air - vac_to_air(vac))
    return vac


def flux_to_mag(flux, err=None):
    """Magnitude of a flux (zero point 0), and its error when the flux error is given (2.5 / ln 10 · σ / f)."""
    f = np.asarray(flux, float)
    mag = -2.5 * np.log10(f)
    return mag if err is None else (mag, 2.5 / np.log(10) * np.asarray(err, float) / f)


def mag_to_flux(mag, err=None):
    """Flux of a magnitude (zero point 0), and its error when the magnitude error is given."""
    f = 10 ** (-0.4 * np.asarray(mag, float))
    return f if err is None else (f, f * np.log(10) / 2.5 * np.asarray(err, float))
