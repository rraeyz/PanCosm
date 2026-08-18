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

from .hdr import get, number

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


# keywords that hold the time of day when DATE-OBS has the date only (IRAF, NOAO, MaxIm, ... spell it differently)
TIME_KEYS = ("TIME-OBS", "TIME_OBS", "UT", "UTSTART", "UT-START", "UT_START", "UTC", "UTC-OBS", "UT-OBS")


def _date_and_time(value, header):
    """An ISO date-time from a DATE-OBS value, completed by a time-of-day keyword when it holds the date only.
    None when no time of day is known (a date alone is not an observation time: it would silently mean 00:00)."""
    value = value.strip()
    old = re.fullmatch(r"(\d\d)/(\d\d)/(\d\d)", value)  # FITS before 1999: dd/mm/yy
    if old:
        value = f"19{old.group(3)}-{old.group(2)}-{old.group(1)}"
    if re.match(r"\d{4}-\d\d-\d\d \d", value):  # a space instead of the T
        value = value.replace(" ", "T", 1)
    if "T" in value:
        return value
    for key in TIME_KEYS:
        tod = header.get(key)
        if isinstance(tod, str) and re.match(r"\s*\d{1,2}:\d\d", tod):
            return f"{value}T{tod.strip()}"
    return None


def start_time(header) -> Time:
    """Exposure start in UTC. Prefers explicit UT keywords; MJD/JD only when nothing better exists
    (some cameras round them to 0.001 d = 86 s)."""
    date_only = None
    for key in ("UT-OBS", "DATE-BEG", "DATE-OBS", "DATE_OBS"):
        value = header.get(key)
        if not value or not isinstance(value, str) or not re.match(r"\s*(\d{4}-|\d\d/)", value):
            continue
        full = _date_and_time(value, header)
        if full is None:
            date_only = key
            continue
        try:
            return _parse_iso(full)
        except ValueError:
            continue
    for key, fmt in (("JD-OBS", "jd"), ("JD", "jd"), ("MJD-OBS", "mjd"), ("MJD", "mjd")):
        if key in header:
            if number(header[key]) is not None:
                return Time(number(header[key]), format=fmt, scale="utc")
    if date_only:
        raise TimeError(f"{date_only} holds a date but no time of day, and no time keyword was found")
    raise TimeError(
        "no observation time in header (DATE-OBS, UT-OBS, JD, MJD-OBS): add DATE-OBS on the Images page's Header tab"
    )


def mid_time(header) -> Time:
    """Mid-exposure UTC. JD-MID / DATE-AVG are used as given when present."""
    if header.get("DATE-AVG"):
        return _parse_iso(header["DATE-AVG"])
    if number(header.get("JD-MID")) is not None:
        return Time(number(header["JD-MID"]), format="jd", scale="utc")
    note = header.comments["DATE-OBS"] if hasattr(header, "comments") and "DATE-OBS" in header else ""
    if re.search(r"\b(median|mid|middle)\b", note, re.I) and "T" in str(header["DATE-OBS"]):
        return _parse_iso(header["DATE-OBS"])  # LAMOST: 'The observation median UTC'
    exptime = get(header, "EXPTIME", "EXPOSURE", "EXP_TIME", "ITIME", default=0.0)
    return start_time(header) + TimeDelta(exptime / 2, format="sec")


def location(header) -> EarthLocation | None:
    """Observatory from SITELAT/SITELONG (or LAT-OBS/LONG-OBS, OBSGEO-*, ESO TEL GEOLAT/GEOLON, BeSS BSS_LAT/BSS_LONG
    or GEO_LAT/GEO_LONG). Longitude east-positive.

    Plain LATITUDE/LONGITUD are not trusted: some cameras write west-positive longitudes."""
    if all(k in header for k in ("OBSGEO-X", "OBSGEO-Y", "OBSGEO-Z")):
        return EarthLocation.from_geocentric(header["OBSGEO-X"], header["OBSGEO-Y"], header["OBSGEO-Z"], unit=u.m)
    for lat_key, lon_key in (
        ("SITELAT", "SITELONG"),
        ("LAT-OBS", "LONG-OBS"),
        ("OBSGEO-B", "OBSGEO-L"),
        ("HIERARCH ESO TEL GEOLAT", "HIERARCH ESO TEL GEOLON"),  # ESO: east-positive degrees
        ("BSS_LAT", "BSS_LONG"),  # BeSS / ARAS amateur spectra, east-positive
        ("GEO_LAT", "GEO_LONG"),
    ):
        if lat_key in header and lon_key in header:
            lat = _angle(header[lat_key])
            lon = _longitude(header, _angle(header[lon_key]))
            if lat == 0 and lon == 0:  # BeSS files write 0, 0 for an unknown site
                continue
            height = get(
                header,
                "SITEELEV",
                "ALT-OBS",
                "OBSGEO-H",
                "HIERARCH ESO TEL GEOELEV",
                "BSS_ELEV",
                "GEO_ELEV",
                default=0.0,
            )
            return EarthLocation.from_geodetic(lon * u.deg, lat * u.deg, height * u.m)
    if "LATITUDE" in header and "LONGITUD" in header:  # used when the sign of the longitude is known
        lon = _angle(header["LONGITUD"])
        sign = _sign_from_lst(header, lon)
        note = header.comments["LONGITUD"].lower() if hasattr(header, "comments") else ""
        if sign is None and re.search(r"e\+|east|degrees e\b|\(e\)", note):  # Palomar, Tartu
            sign = 1
        elif sign is None and re.search(r"w\+|west", note):
            sign = -1
        if sign:
            height = get(header, "SITEELEV", "ALT-OBS", "OBSGEO-H", default=0.0)
            return EarthLocation.from_geodetic(sign * lon * u.deg, _angle(header["LATITUDE"]) * u.deg, height * u.m)
    return None


def _sign_from_lst(header, lon):
    """+1 or -1 when the local sidereal time in the header agrees with the longitude read east- or
    west-positive, None when it cannot tell (no LST, no time, or neither agrees)."""
    lst = header.get("LST", header.get("SIDEREAL", header.get("ST")))
    if lst is None:
        return None
    try:
        from astropy.coordinates import Angle

        t, given = start_time(header), Angle(lst, unit=u.hourangle).hour

        def miss(deg):
            d = abs(t.sidereal_time("apparent", longitude=deg * u.deg).hour - given) % 24
            return min(d, 24 - d)

        sign = min((1, -1), key=lambda s: miss(s * lon))
        return sign if miss(sign * lon) < 0.05 else None  # within 3 minutes (the LST at start or mid-exposure)
    except Exception:  # an unreadable LST or no Earth-orientation data
        return None


def _longitude(header, lon):
    """Some control systems (MaxIm DL with ACE, e.g. at TUBITAK National Observatory) write SITELONG in hours
    ('02 01 20.533' is 30.33 deg). When the header has the local sidereal time, the reading of the longitude that
    agrees with it is taken; without it the value is taken as degrees."""
    lst = header.get("SIDEREAL", header.get("LST"))
    if lst is None or abs(lon) > 24:
        return lon
    try:
        from astropy.coordinates import Angle

        t = start_time(header)
        given = Angle(lst, unit=u.hourangle).hour

        def miss(deg):
            d = abs(t.sidereal_time("mean", longitude=deg * u.deg).hour - given) % 24
            return min(d, 24 - d)

        return min((lon, lon * 15), key=miss) if min(miss(lon), miss(lon * 15)) < 0.05 else lon
    except Exception:  # no time, an unreadable LST or no Earth-orientation data: keep degrees
        return lon


def _angle(value) -> float:
    if isinstance(value, str) and (":" in value or " " in value.strip()):
        from astropy.coordinates import Angle

        try:
            return Angle(value, unit=u.deg).deg
        except ValueError:  # '39.9 deg N' and such: the number in front
            pass
    x = number(value)
    if x is None:
        raise ValueError(f"not an angle: {value!r}")
    return x


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


def chronological(paths, times=None) -> list[str]:
    """Paths sorted by mid-exposure time from their headers (file names are not always in time order:
    frame-to-frame tracking depends on it). Files without a readable time follow, in name order. times: a dict that
    receives {path: mid-exposure UTC JD}, so a frame list need not open every file again (18 758 TESS cadences:
    the Photometry page read every header twice, 98 s)."""
    from astropy.io import fits

    from .io.fits import find_image_hdu

    timed, untimed = [], []
    for p in sorted(str(p) for p in paths):
        try:
            with fits.open(p) as hdul:
                timed.append((mid_time(hdul[find_image_hdu(hdul)].header).jd, p))
        except (TimeError, ValueError, OSError):
            untimed.append(p)
    if times is not None:
        times.update({p: jd for jd, p in timed})
    return [p for _, p in sorted(timed)] + untimed
