"""Ground-based survey and database light curves: AAVSO (International Database), ZTF (IRSA light-curve
service) and ASAS-SN (Sky Patrol CSV files), read into the light curves the other tools understand.

Each source keeps its own photometric band; one band is chosen (the most numerous unless asked), flagged points
are dropped, magnitudes become relative flux (median 1). Upper limits are kept with the UPPER flag where the source
marks them: AAVSO's "Fainter Than" column or a "<" before the magnitude, ASAS-SN's ">" before it (ZTF's IRSA rows
carry no limit marker); they and AAVSO's visual estimates (band "Vis.") come as their own sets beside the curve,
never in it, so period searches and fits do not see them (PER-1 item 3).
Times: AAVSO gives JD (UTC), ZTF and ASAS-SN give HJD (UTC); they are converted to BJD_TDB with the star's
position (barycentric correction and TDB-UTC), so they can be joined with TESS or the user's own data.
"""

import csv
import io

import numpy as np

from .lightcurve import UPPER

ZTF_URL = "https://irsa.ipac.caltech.edu/cgi-bin/ZTF/nph_light_curves"
AAVSO_URL = "https://www.aavso.org/vsx/index.php"
KEPT = "times kept in {standard}: the star's coordinates are not known, so they are not converted to BJD_TDB"
VISUAL = "Vis."
HJD_TAKEN_AS_UTC = "the times are HJD without a time scale and are taken as UTC: if they are TT, they are {s} s late"


def _get_text(url, params, timeout=60):
    from ..services import http
    from ..services.cache import cached

    def now():
        return http.get(url, params, timeout, agent="Mozilla/5.0").decode("utf-8", errors="replace")

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
    """Rows of a survey CSV as (time, time_kind 'jd' | 'hjd' | 'mjd', mag, err, band, flag), flag UPPER for an
    upper limit (the magnitude is the limit) else 0. Recognises AAVSO (JD, Magnitude/mag, Uncertainty/uncert, Band,
    Fainter Than), ZTF (hjd/mjd, mag, magerr, filtercode, catflags) and ASAS-SN Sky Patrol (HJD, mag, mag_err,
    Filter)."""
    out = []
    for row in _rows(text):
        mag_text = _pick(row, "mag", "magnitude")
        if mag_text is None:
            continue
        fainter = _pick(row, "fainter than", "fainterthan", "fainter_than")
        upper = mag_text.startswith((">", "<")) or bool(fainter and fainter not in ("0", "no", "false"))
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
            out.append((t, kind, m, err, band, UPPER if upper else 0))
    return out


def _limit(row):
    return len(row) > 5 and bool(row[5] & UPPER)


def to_light_curve(rows, coord=None, band=None, source=""):
    """Relative-flux light curve of one band's measurements. With coord (SkyCoord) times become BJD_TDB.
    Beside it, on the same flux scale and never in it: "upper_limits" (of the band and the visual estimates) and,
    when the band is not visual, "visual" (AAVSO's visual estimates), each {time, rel_flux, mag}."""
    if not rows:
        raise ValueError("no measurements in the file")
    bands = [r[4] for r in rows]
    measured = [r[4] for r in rows if not _limit(r)]
    band = band or (max(set(measured), key=measured.count) if measured else bands[0])
    sel = [r for r in rows if r[4] == band and not _limit(r)]
    if len(sel) < 3:
        raise ValueError(f"fewer than 3 measurements in band {band}")
    kind = sel[0][1]
    scale = "HJD_UTC" if kind == "hjd" else "JD_UTC"
    extra = {"time_scale_original": scale}
    if coord is None:
        extra["warnings"] = [KEPT.format(standard=scale)]

    def times(t):
        if coord is None or not len(t):
            return np.asarray(t, float)
        from ..core.units import convert_times  # PER-1 item 3: BJD_TDB on load, the original standard kept

        return convert_times(np.asarray(t, float), scale, coord)["BJD_TDB"]

    t = times([r[0] for r in sel])
    m = np.array([r[2] for r in sel])
    e = np.array([r[3] for r in sel])
    order = np.argsort(t)
    t, m, e = t[order], m[order], e[order]
    ref = np.median(m)
    flux = 10 ** (-0.4 * (m - ref))

    def aside(picked):
        ts, ms = times([r[0] for r in picked]), np.array([r[2] for r in picked], float)
        o = np.argsort(ts)
        return {"time": ts[o].tolist(), "rel_flux": (10 ** (-0.4 * (ms[o] - ref))).tolist(), "mag": ms[o].tolist()}

    extra["upper_limits"] = aside([r for r in rows if r[4] in (band, VISUAL) and _limit(r)])
    if band != VISUAL and any(r[4] == VISUAL and not _limit(r) for r in rows):
        extra["visual"] = aside([r for r in rows if r[4] == VISUAL and not _limit(r)])
    return {
        "time": t.tolist(),
        "rel_flux": flux.tolist(),
        "rel_flux_err": (flux * np.where(np.isfinite(e), e, np.nan) / 1.0857).tolist(),
        "mag": m.tolist(),
        "time_scale": "BJD_TDB" if coord is not None else scale,
        "band": band,
        "bands": sorted(set(bands)),
        "source": f"{source} {band}".strip(),
    } | extra


def hjd_notes(text, times):
    """The note of ARC-15's rule when a file says HJD without a time scale (taken as UTC), else []."""
    from .ephemeris import hjd_scale_unknown

    seconds = hjd_scale_unknown(text, times)
    return [HJD_TAKEN_AS_UTC.format(s=f"{seconds:.0f}")] if seconds else []


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
