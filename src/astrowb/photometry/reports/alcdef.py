"""ALCDEF light-curve block for an asteroid night (plans/photometry.md PHO-21), written against "ALCDEF Definition and
Standards v. 2.3.0, 2024 March 4" (alcdef.org/docs/ALCDEF_Standard.pdf). Section numbers below are that document's.

    write(path, session)      session: the measured night (dict, keys below); lines of keyword=value, LF, UTF-8 no BOM
    profile_fields(profile)   the session keys the observer/equipment profile can fill

Rules followed (section): file layout, STARTMETADATA first, ENDMETADATA, DATA lines, ENDDATA, no blank lines, lines
<= 255 characters, at least two DATA lines (1.1, 1.1.1-1.1.3); DATA=JD|MAG|MAGERR with PIPE, JD standard (not MJD)
to 6 decimals, magnitudes signed with 3 decimals (1.1.3, 2, 5 DATA); decimal point, signed numbers, leading zero
(2); keyword order follows the sample block of Appendix A.

Required keywords written (every one raises ValueError when it has no value): OBJECTNUMBER, OBJECTNAME (5, 4.1),
SESSIONDATE and SESSIONTIME (5; the mid-time of the data, which 4.3.1 asks to be within 15 minutes of the data's
mean JD), CONTACTNAME, CONTACTINFO, OBSERVERS (5), FILTER, MAGBAND (5), DIFFERMAGS, STANDARD (5, 4.3.2),
LTCAPP, LTCTYPE (5), REDUCEDMAGS (5), DELIMITER (5), STARTMETADATA, ENDMETADATA, DATA, ENDDATA (5). Required by a
cross-check: LTCDAYS (non-zero) when LTCAPP is AVERAGE/POINT with LTCTYPE=LIGHTTIME, UCORMAG (non-zero) when
REDUCEDMAGS is AVERAGE/POINT (5), DIFFZEROMAG (> 0) when DIFFERMAGS=TRUE with STANDARD INTERNAL/TRANSFORMED (4.3.2).
Always written with the standard's own defaults: REVISEDDATA (FALSE, 5), SUBMITPDS (FALSE, 3.1: every v2.2+ block
carries it, opt-in), CICORRECTION=FALSE (5; no colour correction is applied here), EXPJD=MID (5).
Written when given: MPCDESIG (empty when none, 5), MPCCODE, FACILITY, OBSLONGITUDE/OBSLATITUDE (east-positive,
-180..+180, -90..+90), TELESCOPE, DETECTOR, EXPOSURE (whole seconds), OBJECTRA (HH:MM.m) and OBJECTDEC (+-DD MM) from
degrees, EQUINOX=J2000.0 with them, PHASE, PABL, PABB, COMMENT lines (each line <= 255 characters, all < 2048).
Not written: comparison-star keywords (1.2, optional), BIBCODE, PUBLICATION, constant keywords (3.2, defined by the
site manager only).

session keys: jd, mag, mag_err (lists; mag_err may be None), object_number (0 when unnumbered), object_name,
mpc_desig, session_date/session_time (default: from the mean JD), contact_name, contact_info, observers, filter,
magband, differmags (bool), standard, diffzeromag, ltcapp, ltcdays, reducedmags, ucormag, submit_pds, revised_data,
exposure, mpc_code, facility, lon, lat, telescope, detector, ra, dec (deg), phase, pabl, pabb, comments (list).
"""

import math
from datetime import datetime, timedelta

BANDS = (
    "B",
    "V",
    "R",
    "I",
    "PU",
    "PG",
    "PR",
    "PI",
    "PZ",
    "SU",
    "SG",
    "SR",
    "SI",
    "SZ",
    "AC",
    "AO",
    "GB",
    "GG",
    "GR",
    "J",
    "K",
    "H",
)
FILTERS = (*BANDS, "PAZ", "C")  # 5 FILTER: standard filters, C for none or clear
STANDARDS = ("NONE", "INTERNAL", "TRANSFORMED")
CORRECTIONS = ("NONE", "AVERAGE", "POINT")
LIMITS = {
    "OBJECTNAME": 30,
    "MPCDESIG": 30,
    "CONTACTNAME": 80,
    "CONTACTINFO": 120,
    "FACILITY": 80,
    "TELESCOPE": 40,
    "DETECTOR": 40,
    "MPCCODE": 10,
}


def _bad(keyword, reason):
    return f"ALCDEF keyword {keyword} is not valid: {reason}"


def _need(s, key, keyword):
    v = s.get(key)
    if v is None or (isinstance(v, str) and not v.strip()):
        raise ValueError(f"ALCDEF needs a value for {keyword}")
    return v


def _choice(s, key, keyword, allowed):
    v = _need(s, key, keyword)
    if v not in allowed:
        raise ValueError(_bad(keyword, f"{v} is not one of {', '.join(allowed)}"))
    return v


def _num(s, key, keyword, lo=None, hi=None):
    v = float(_need(s, key, keyword))
    if not math.isfinite(v) or (lo is not None and not lo <= v <= hi):
        raise ValueError(_bad(keyword, f"{v} is outside {lo} to {hi}" if lo is not None else f"{v} is not a number"))
    return v


def _jd_utc(jd):
    return datetime(1970, 1, 1) + timedelta(days=jd - 2440587.5)


def profile_fields(profile):
    """The session keys the profile fills: contact name, observers, MPC code, and, once a site name is entered
    (the profile's coordinates are Ankara defaults until then), the facility and its position."""
    obs, site = profile.get("observer") or {}, profile.get("site") or {}
    out = {"contact_name": obs.get("name"), "observers": obs.get("observers"), "mpc_code": obs.get("mpc_code")}
    if site.get("name"):
        out |= {"facility": site["name"], "lat": site.get("lat"), "lon": site.get("lon")}
    return {k: v for k, v in out.items() if v not in (None, "")}


def _ra_dec(ra, dec):
    tenths = round(float(ra) % 360 / 15 * 600) % 14400  # tenths of a minute of time
    h, m = divmod(tenths, 600)
    minutes = round(abs(float(dec)) * 60)
    return f"{h:02d}:{m // 10:02d}.{m % 10}", f"{'-' if dec < 0 else '+'}{minutes // 60:02d} {minutes % 60:02d}"


def _optional(s):
    out = []
    for key, kw in (("facility", "FACILITY"), ("mpc_code", "MPCCODE")):
        if s.get(key):
            out.append(f"{kw}={s[key]}")
    if s.get("lon") is not None:
        out.append(f"OBSLONGITUDE={_num(s, 'lon', 'OBSLONGITUDE', -180, 180):+.5f}")
    if s.get("lat") is not None:
        out.append(f"OBSLATITUDE={_num(s, 'lat', 'OBSLATITUDE', -90, 90):+.5f}")
    for key in ("telescope", "detector"):
        if s.get(key):
            out.append(f"{key.upper()}={s[key]}")
    if s.get("exposure") is not None:
        out.append(f"EXPOSURE={int(_num(s, 'exposure', 'EXPOSURE', 1, 65535))}")  # whole seconds, 5 EXPOSURE
    out.append("EXPJD=MID")
    if s.get("ra") is not None and s.get("dec") is not None:
        ra, dec = _ra_dec(s["ra"], s["dec"])
        out += [f"OBJECTRA={ra}", f"OBJECTDEC={dec}", "EQUINOX=J2000.0"]
    if s.get("phase") is not None:
        out.append(f"PHASE={_num(s, 'phase', 'PHASE', -180, 180):+.2f}")
    if s.get("pabl") is not None:
        out.append(f"PABL={_num(s, 'pabl', 'PABL', 0, 359.9):+.1f}")
    if s.get("pabb") is not None:
        out.append(f"PABB={_num(s, 'pabb', 'PABB', -90, 90):+.1f}")
    return out


def _corrections(s, zero, ltc, red):
    out = []
    if zero is not None:
        out.append(f"DIFFZEROMAG={zero:+.3f}")
    out += ["CICORRECTION=FALSE", f"LTCAPP={ltc}", f"LTCTYPE={'NONE' if ltc == 'NONE' else 'LIGHTTIME'}"]
    if ltc != "NONE":
        days = _num(s, "ltcdays", "LTCDAYS", -1, 1)
        if days == 0:
            raise ValueError(_bad("LTCDAYS", "must not be zero when a light-time correction is applied"))
        out.append(f"LTCDAYS={days:+.6f}")
    out.append(f"REDUCEDMAGS={red}")
    if red != "NONE":
        u = _num(s, "ucormag", "UCORMAG", -100, 100)
        if u == 0:
            raise ValueError(_bad("UCORMAG", "must not be zero when magnitudes are reduced"))
        out.append(f"UCORMAG={u:+.3f}")
    return out


def _data(jd, mag, err):
    err = err if err is not None else [None] * len(jd)
    return [
        f"DATA={j:.6f}|{m:+.3f}" + ("" if e is None else f"|{float(e):+.3f}")
        for j, m, e in zip(jd, mag, err, strict=True)
    ]


def lines(session):
    s = session
    jd = [float(x) for x in s.get("jd") or []]
    mag = [float(x) for x in s.get("mag") or []]
    err = s.get("mag_err")
    if len(jd) < 2 or len(jd) != len(mag) or (err is not None and len(err) != len(jd)):
        raise ValueError(_bad("DATA", "at least two observations with a time and magnitude each are needed"))
    if not all(map(math.isfinite, jd + mag)) or (err is not None and not all(math.isfinite(float(e)) for e in err)):
        raise ValueError(_bad("DATA", "a time, magnitude or error is not finite"))
    if min(jd) < 2000000:
        raise ValueError(_bad("DATA", "times must be Julian Dates, not modified Julian Dates"))
    number = _need(s, "object_number", "OBJECTNUMBER")
    if int(number) != number or not 0 <= number <= 4294967295:
        raise ValueError(_bad("OBJECTNUMBER", "must be a whole number from 0 (unnumbered) up"))
    mid = _jd_utc((min(jd) + max(jd)) / 2) + timedelta(seconds=0.5)  # rounded to the second
    differ = bool(s.get("differmags"))
    standard = _choice(s, "standard", "STANDARD", STANDARDS)
    if not differ and standard == "NONE":  # 4.3.2: sky magnitudes are on an internal or a standard system
        raise ValueError(_bad("STANDARD", "magnitudes that are not differential need INTERNAL or TRANSFORMED"))
    zero = None
    if differ and standard != "NONE":
        zero = _num(s, "diffzeromag", "DIFFZEROMAG", 1e-6, 1e3)
    ltc = _choice(s, "ltcapp", "LTCAPP", CORRECTIONS)
    red = _choice(s, "reducedmags", "REDUCEDMAGS", CORRECTIONS)
    out = [
        "STARTMETADATA",
        f"REVISEDDATA={'TRUE' if s.get('revised_data') else 'FALSE'}",
        f"SUBMITPDS={'TRUE' if s.get('submit_pds') else 'FALSE'}",
        f"OBJECTNUMBER={int(number)}",
        f"OBJECTNAME={_need(s, 'object_name', 'OBJECTNAME')}",
        f"MPCDESIG={s.get('mpc_desig') or ''}",
        f"SESSIONDATE={s.get('session_date') or f'{mid:%Y-%m-%d}'}",
        f"SESSIONTIME={s.get('session_time') or f'{mid:%H:%M:%S}'}",
        f"CONTACTNAME={_need(s, 'contact_name', 'CONTACTNAME')}",
        f"CONTACTINFO={_need(s, 'contact_info', 'CONTACTINFO')}",
        f"OBSERVERS={_need(s, 'observers', 'OBSERVERS')}",
    ]
    out += _optional(s)
    out += [
        f"FILTER={_choice(s, 'filter', 'FILTER', FILTERS)}",
        f"MAGBAND={_choice(s, 'magband', 'MAGBAND', BANDS)}",
        f"DIFFERMAGS={'TRUE' if differ else 'FALSE'}",
        f"STANDARD={standard}",
    ]
    out += _corrections(s, zero, ltc, red)
    out.append("DELIMITER=PIPE")
    comments = [str(c) for c in s.get("comments") or []]
    out += [f"COMMENT={c}" for c in comments]
    if sum(len(c) + 2 for c in comments) >= 2048:
        raise ValueError(_bad("COMMENT", "all comment lines together must be shorter than 2048 characters"))
    out.append("ENDMETADATA")
    out += _data(jd, mag, err)
    out.append("ENDDATA")
    for line in out:
        key = line.partition("=")[0]
        if len(line) > 255 or len(line.partition("=")[2]) > LIMITS.get(key, 255):
            raise ValueError(_bad(key, "the value is too long"))
    return out


def write(path, session):
    text = "\n".join(lines(session)) + "\n"  # built first: a rejected session leaves no half file
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path
