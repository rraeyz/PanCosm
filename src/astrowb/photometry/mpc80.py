"""MPC 80-column optical observation lines, https://minorplanetcenter.net/iau/info/OpticalObs.html

Columns (1-based): 1-12 packed designation, 14 note 1, 15 note 2 ('C' = CCD), 16-32 date "YYYY MM DD.dddddd" (UT),
33-44 RA "HH MM SS.ddd", 45-56 Dec "sDD MM SS.dd", 66-70 magnitude, 71 band, 78-80 observatory code. The rest is blank.
"""

from datetime import datetime, timedelta

_CENTURY = {18: "I", 19: "J", 20: "K"}


def pack_designation(designation):
    """12-column packed form: a number below 100000 ('433' -> '00433'), a provisional designation
    ('2024 AB1' -> '     K24A01B'). Anything else (a temporary name) is used as given, cut to 12 characters
    (shortcut: no packing of numbers from 100000 or of cycle counts from 100, the MPC's longer forms)."""
    d = str(designation).strip()
    if d.isdigit() and int(d) < 100000:
        return f"{int(d):05d}" + " " * 7
    parts = d.split()
    if len(parts) == 2 and len(parts[0]) == 4 and parts[0].isdigit() and len(parts[1]) >= 2 and parts[1][:2].isalpha():
        century = _CENTURY.get(int(parts[0][:2]))
        tail = parts[1][2:]
        if century and (tail == "" or (tail.isdigit() and int(tail) < 100)):
            return f"     {century}{parts[0][2:]}{parts[1][0]}{int(tail or 0):02d}{parts[1][1]}"
    return d[:12].ljust(12)


def _date(iso):
    """'YYYY MM DD.dddddd' with the day fraction rounded to 1e-6 day (a carry moves to the next day)."""
    t = datetime.fromisoformat(iso.rstrip("Z"))
    midnight = t.replace(hour=0, minute=0, second=0, microsecond=0)
    micro = round((t - midnight).total_seconds() / 86400 * 1e6)
    t = midnight + timedelta(days=micro // 10**6)
    return f"{t.year:04d} {t.month:02d} {t.day:02d}.{micro % 10**6:06d}"


def _ra(deg):
    n = round((deg % 360) / 15 * 3600 * 1000) % (24 * 3600 * 1000)  # milliseconds of time
    h, n = divmod(n, 3600000)
    m, n = divmod(n, 60000)
    return f"{h:02d} {m:02d} {n // 1000:02d}.{n % 1000:03d}"


def _dec(deg):
    n = round(abs(deg) * 3600 * 100)  # hundredths of an arcsecond
    d, n = divmod(n, 360000)
    m, n = divmod(n, 6000)
    return f"{'-' if deg < 0 else '+'}{d:02d} {m:02d} {n // 100:02d}.{n % 100:02d}"


def mpc80_lines(rows, designation, mpc_code="", band=""):
    """One 80-column line per row ({time ISO UTC, ra, dec in degrees, optional mag}). A missing observatory code or
    magnitude stays blank."""
    pk = pack_designation(designation)
    out = []
    for r in rows:
        mag = r.get("mag")
        mag_s = f"{mag:5.1f}" if mag is not None else " " * 5
        b = (band or " ") if mag is not None else " "
        line = f"{pk} " + " C" + _date(r["time"]) + _ra(r["ra"]) + _dec(r["dec"]) + " " * 9 + mag_s + b
        out.append(line.ljust(77) + str(mpc_code or "").strip().upper().ljust(3))
    return out


def mpc80_text(rows, designation, mpc_code="", band=""):
    if not designation:
        raise ValueError("designation, observatory code and observer names are required")
    return "\n".join(mpc80_lines(rows, designation, mpc_code, band)) + "\n"
