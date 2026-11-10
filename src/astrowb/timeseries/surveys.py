"""Ground-based survey and database light curves: AAVSO (International Database), ZTF (IRSA light-curve
service) and ASAS-SN (Sky Patrol CSV files), read into the light curves the other tools understand.

Each source keeps its own photometric band; one band is chosen (the most numerous unless asked), upper
limits ("fainter than") and flagged points are dropped, magnitudes become relative flux (median 1).
Times: AAVSO gives JD (UTC), ZTF and ASAS-SN give HJD (UTC); they are converted to BJD_TDB with the star's
position (barycentric correction and TDB-UTC), so they can be joined with TESS or the user's own data.
"""

import csv
import io
import urllib.parse
import urllib.request

import numpy as np

ZTF_URL = "https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves"
AAVSO_URL = "https://www.aavso.org/vsx/index.php"


def _get_text(url, params, timeout=60):
    from ..services.cache import cached

    def now():
        req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (fixed https archive URLs)
            return r.read().decode("utf-8", errors="replace")

    return cached("lightcurves", (url, params), now)


def _rows(text):
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    dialect = "excel-tab" if lines and "\t" in lines[0] and "," not in lines[0] else "excel"
    reader = csv.DictReader(io.StringIO("\n".join(lines)), dialect=dialect)
    # extra cells (a row longer than the header, trailing commas) come as a list under the key None: left out
    return [
        {k.strip().lower(): (v or "").strip() for k, v in row.items() if isinstance(k, str) and not isinstance(v, list)}
        for row in reader
    ]


def _pick(row, *names):
    for n in names:
        if n in row and row[n] != "":
            return row[n]
    return None


def _num(text):
    try:
        return float(str(text).lstrip("<>"))
    except (TypeError, ValueError):
        return np.nan


def parse(text):
    """Rows of a survey CSV as (time, time_kind 'jd' | 'hjd' | 'mjd', mag, err, band). Recognises AAVSO
    (JD, Magnitude/mag, Uncertainty/uncert, Band, Fainter Than), ZTF (hjd/mjd, mag, magerr, filtercode,
    catflags) and ASAS-SN Sky Patrol (HJD, mag, mag_err, Filter)."""
    out = []
    for row in _rows(text):
        mag_text = _pick(row, "mag", "magnitude")
        if mag_text is None or mag_text.startswith((">", "<")):
            continue  # upper limit
        fainter = _pick(row, "fainter than", "fainterthan", "fainter_than")
        if fainter and fainter not in ("0", "no", "false"):
            continue
        if _pick(row, "catflags") not in (None, "0"):
            continue  # ZTF: flagged
        if "hjd" in row and row["hjd"]:
            t, kind = _num(row["hjd"]), "hjd"
        elif _pick(row, "jd") is not None:
            t, kind = _num(row["jd"]), "jd"
        elif _pick(row, "mjd") is not None:
            t, kind = _num(row["mjd"]) + 2400000.5, "jd"
        else:
            continue
        err = _num(_pick(row, "uncertainty", "uncert", "magerr", "mag_err", "err"))
        band = _pick(row, "band", "filtercode", "filter", "phot_filter") or "?"
        m = _num(mag_text)
        if np.isfinite(t) and np.isfinite(m):
            out.append((t, kind, m, err, band))
    return out


def to_light_curve(rows, coord=None, band=None, source=""):
    """Relative-flux light curve of one band. With coord (SkyCoord) times become BJD_TDB."""
    if not rows:
        raise ValueError("no measurements in the file")
    bands = [r[4] for r in rows]
    band = band or max(set(bands), key=bands.count)
    sel = [r for r in rows if r[4] == band]
    if len(sel) < 3:
        raise ValueError(f"fewer than 3 measurements in band {band}")
    t = np.array([r[0] for r in sel])
    kind = sel[0][1]
    m = np.array([r[2] for r in sel])
    e = np.array([r[3] for r in sel])
    scale = "HJD_UTC" if kind == "hjd" else "JD_UTC"
    if coord is not None:
        t, scale = _bjd(t, kind, coord), "BJD_TDB"
    order = np.argsort(t)
    t, m, e = t[order], m[order], e[order]
    flux = 10 ** (-0.4 * (m - np.median(m)))
    return {
        "time": t.tolist(),
        "rel_flux": flux.tolist(),
        "rel_flux_err": (flux * np.where(np.isfinite(e), e, np.nan) / 1.0857).tolist(),
        "mag": m.tolist(),
        "time_scale": scale,
        "band": band,
        "bands": sorted(set(bands)),
        "source": f"{source} {band}".strip(),
    }


def _bjd(t, kind, coord):
    """JD (UTC) or HJD (UTC) to BJD_TDB at the geocentre (ground-based surveys; the topocentric part is
    below 0.02 s)."""
    import astropy.units as u
    from astropy.coordinates import EarthLocation
    from astropy.time import Time

    geo = EarthLocation.from_geocentric(0, 0, 0, unit=u.m)
    times = Time(t, format="jd", scale="utc", location=geo)
    if kind == "hjd":  # remove the heliocentric light time to get back to the observation time, then barycentre
        times = times - times.light_travel_time(coord, kind="heliocentric")
        times = Time(times.jd, format="jd", scale="utc", location=geo)
    return (times.tdb + times.light_travel_time(coord, kind="barycentric")).jd


def ztf(coord, fetch=None, radius_arcsec=2.0):
    """ZTF light curves around a position from IRSA (all bands; choose one with to_light_curve)."""
    text = (fetch or _get_text)(
        ZTF_URL,
        {
            "POS": f"CIRCLE {coord.ra.deg:.6f} {coord.dec.deg:.6f} {radius_arcsec / 3600:.6f}",
            "FORMAT": "csv",
            "BAD_CATFLAGS_MASK": "32768",
        },
    )
    return parse(text)


def aavso(name, fetch=None, from_jd=None, to_jd=None):
    """Observations of a star from the AAVSO International Database (VSX data API)."""
    params = {"view": "api.delim", "ident": name, "delimiter": ","}
    if from_jd:
        params["fromjd"] = f"{from_jd:.1f}"
    if to_jd:
        params["tojd"] = f"{to_jd:.1f}"
    return parse((fetch or _get_text)(AAVSO_URL, params))
