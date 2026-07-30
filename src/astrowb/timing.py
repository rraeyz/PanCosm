"""Observation times: header -> mid-exposure UTC -> JD / HJD / BJD_TDB, and airmass.

Times are always float64 on the CPU (a float32 JD has ~1 minute resolution). Works offline:
UTC->TDB needs only the leap-second table shipped with astropy; the barycentric correction
uses astropy's built-in solar-system ephemeris. Observatory position changes BJD by at most
~21 ms; when the header has none, the geocentre is used.
"""

import re

import astropy.units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time, TimeDelta
from astropy.utils import iers

# Observatories are often offline: never block on an IERS download; for dates beyond the bundled
# table astropy then warns and uses predictions (affects airmass/alt-az only, not BJD).
iers.conf.auto_download = False
iers.conf.iers_degraded_accuracy = "warn"

_GEOCENTRE = EarthLocation.from_geocentric(0, 0, 0, unit=u.m)
_TZ = re.compile(r"([+-])(\d{2}):?(\d{2})$")


class TimeError(ValueError):
    pass


def _parse_iso(text: str) -> Time:
    """ISO date-time, optionally with a time-zone offset like -0700 or +03:00 (converted to UTC)."""
    text = text.strip()
    if text.endswith("Z"):
        text = text[:-1]
    m = _TZ.search(text[10:]) if len(text) > 10 else None
    offset_h = 0.0
    if m:
        sign = -1 if m.group(1) == "-" else 1
        offset_h = sign * (int(m.group(2)) + int(m.group(3)) / 60)
        text = text[: 10 + m.start()]
    return Time(text, format="isot", scale="utc") - TimeDelta(offset_h * 3600, format="sec")


def start_time(header) -> Time:
    """Exposure start in UTC. Prefers explicit UT keywords; MJD/JD only when nothing better exists
    (some cameras round them to 0.001 d = 86 s)."""
    for key in ("UT-OBS", "DATE-BEG", "DATE-OBS", "DATE_OBS"):
        value = header.get(key)
        if not value or not isinstance(value, str):
            continue
        if "T" not in value and header.get("TIME-OBS", header.get("UT")):  # old style: date and time apart
            value = f"{value}T{header.get('TIME-OBS', header.get('UT'))}"
        try:
            return _parse_iso(value)
        except ValueError:
            continue
    for key, fmt in (("JD-OBS", "jd"), ("JD", "jd"), ("MJD-OBS", "mjd")):
        if key in header:
            return Time(float(header[key]), format=fmt, scale="utc")
    raise TimeError("no observation time in header (DATE-OBS, UT-OBS, JD, MJD-OBS)")


def mid_time(header) -> Time:
    """Mid-exposure UTC. JD-MID / DATE-AVG are used as given when present."""
    if header.get("DATE-AVG"):
        return _parse_iso(header["DATE-AVG"])
    if "JD-MID" in header:
        return Time(float(header["JD-MID"]), format="jd", scale="utc")
    exptime = float(header.get("EXPTIME", header.get("EXPOSURE", 0.0)) or 0.0)
    return start_time(header) + TimeDelta(exptime / 2, format="sec")


def location(header) -> EarthLocation | None:
    """Observatory from SITELAT/SITELONG (or LAT-OBS/LONG-OBS, OBSGEO-*). Longitude east-positive.

    Plain LATITUDE/LONGITUD are not trusted: some cameras write west-positive longitudes."""
    if all(k in header for k in ("OBSGEO-X", "OBSGEO-Y", "OBSGEO-Z")):
        return EarthLocation.from_geocentric(header["OBSGEO-X"], header["OBSGEO-Y"], header["OBSGEO-Z"], unit=u.m)
    for lat_key, lon_key in (("SITELAT", "SITELONG"), ("LAT-OBS", "LONG-OBS"), ("OBSGEO-B", "OBSGEO-L")):
        if lat_key in header and lon_key in header:
            lat = _angle(header[lat_key])
            lon = _angle(header[lon_key])
            height = float(header.get("SITEELEV", header.get("ALT-OBS", header.get("OBSGEO-H", 0.0))) or 0.0)
            return EarthLocation.from_geodetic(lon * u.deg, lat * u.deg, height * u.m)
    return None


def _angle(value) -> float:
    if isinstance(value, str) and (":" in value or " " in value.strip()):
        from astropy.coordinates import Angle

        return Angle(value, unit=u.deg).deg
    return float(value)


def bjd_tdb(t: Time, target: SkyCoord, where: EarthLocation | None = None) -> Time:
    """Barycentric Julian Date in TDB for times t (UTC) of a target."""
    t = Time(t, location=_GEOCENTRE if where is None else where)
    return t.tdb + t.light_travel_time(target, kind="barycentric", ephemeris="builtin")


def hjd(t: Time, target: SkyCoord, where: EarthLocation | None = None) -> Time:
    """Heliocentric Julian Date (UTC), still used by many eclipsing-binary catalogues."""
    t = Time(t, location=_GEOCENTRE if where is None else where)
    return t.utc + t.light_travel_time(target, kind="heliocentric", ephemeris="builtin")


def airmass(t: Time, target: SkyCoord, where: EarthLocation) -> float:
    return float(target.transform_to(AltAz(obstime=t, location=where)).secz)


def chronological(paths) -> list[str]:
    """Paths sorted by mid-exposure time from their headers (file names are not always in time order:
    frame-to-frame tracking depends on it). Files without a readable time follow, in name order."""
    from astropy.io import fits

    from .io.fits import find_image_hdu

    timed, untimed = [], []
    for p in sorted(str(p) for p in paths):
        try:
            with fits.open(p) as hdul:
                timed.append((mid_time(hdul[find_image_hdu(hdul)].header).jd, p))
        except (TimeError, ValueError, OSError):
            untimed.append(p)
    return [p for _, p in sorted(timed)] + untimed
