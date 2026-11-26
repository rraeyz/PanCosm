"""Quick period search and exports for the candidates of the variable star search (plans/photometry.md PHO-30)."""

from pathlib import Path

import numpy as np
from astropy.table import Table


def periods(time, corrected, stars):
    """{"star", "period", "power"} lists: the GLS of each star's zero-point-corrected magnitudes on the grid
    timeseries.methods.gls chooses from the time span (NaN when fewer than 10 frames or a span under 0.1 d)."""
    from ..timeseries.methods import gls

    t, m = np.asarray(time, float), np.asarray(corrected, float)
    out = {"star": [int(j) for j in stars], "period": [], "power": []}
    for j in stars:
        ok = np.isfinite(m[:, j])
        if ok.sum() < 10 or np.ptp(t[ok]) / 2 <= 0.05:  # too few frames, or a span shorter than gls's p_min
            out["period"].append(float("nan"))
            out["power"].append(float("nan"))
            continue
        _, power, best = gls(t[ok], m[ok, j])
        out["period"].append(float(best))
        out["power"].append(float(np.max(power)))
    return out


def write_candidates(path, result):
    """CSV of the candidates: position, mean magnitude, indices, flags and the quick period (result: the
    photometry.varfind step's outputs, with "candidate_periods")."""
    v, p = result["variability"], result["candidate_periods"]
    stars = p["star"]
    xy = np.asarray(result["field"]["xy"], float).reshape(-1, 2)
    cols = {"star": stars, "x": xy[stars, 0], "y": xy[stars, 1], "mag": np.asarray(v["mean"])[stars]}
    cols |= {k: np.asarray(a)[stars] for k, a in v["indices"].items()}
    cols |= {"flags": np.asarray(v["flags"])[stars], "period_d": p["period"], "gls_power": p["power"]}
    known = known_columns(result, stars)  # empty until "Look up known variables" was pressed
    cols |= known | {"vsx_period_d": np.ma.masked_invalid(np.asarray(known["vsx_period_d"], float))}
    Table(cols).write(path, format="ascii.csv", overwrite=True)


def write_light_curves(folder, result):
    """One ECSV per candidate (star_<n>.ecsv: time, mag); the files' paths."""
    t = np.asarray(result["field"]["time"], float)
    m = np.asarray(result["variability"]["corrected"], float)
    paths = []
    for j in result["candidate_periods"]["star"]:
        path = Path(folder) / f"star_{j}.ecsv"
        ok = np.isfinite(m[:, j])
        Table({"time": t[ok], "mag": m[ok, j]}).write(path, format="ascii.ecsv", overwrite=True)
        paths.append(path)
    return paths


KNOWN = {"vsx": "", "vsx_type": "", "vsx_period_d": float("nan"), "gcvs": "", "gaia_variable": ""}  # and if missing


def known_variables(field, xy, stars, radius_arcsec=5.0):
    """The candidates' known names: per star (pixel xy on the frame photometry.identify_field solved, field its
    output) the nearest VSX star within radius_arcsec (name, type, period), the nearest GCVS star's name, and
    "VARIABLE" when the nearest Gaia DR3 star carries Gaia's variability flag; KNOWN's empty values where none is
    that close."""
    from astropy.io import fits
    from astropy.wcs import WCS

    xy = np.asarray(xy, float).reshape(-1, 2)
    sky = WCS(fits.Header.fromstring(field["header"])).pixel_to_world(xy[:, 0], xy[:, 1])
    vsx, gcvs, gaia = field.get("variables") or [], field.get("gcvs") or [], field.get("stars") or {}
    iv, ig = (_nearest(sky, [v["ra"] for v in c], [v["dec"] for v in c], radius_arcsec) for c in (vsx, gcvs))
    ia = _nearest(sky, gaia.get("ra", []), gaia.get("dec", []), radius_arcsec)
    flags = gaia.get("variable", [])
    return {
        "star": [int(s) for s in stars],
        "vsx": [vsx[i]["name"] if i >= 0 else "" for i in iv],
        "vsx_type": [vsx[i].get("type", "") if i >= 0 else "" for i in iv],
        "vsx_period_d": [float(vsx[i].get("period") or "nan") if i >= 0 else float("nan") for i in iv],
        "gcvs": [gcvs[i]["name"] if i >= 0 else "" for i in ig],
        "gaia_variable": ["VARIABLE" if i >= 0 and flags[i] else "" for i in ia],
    }


def _nearest(sky, ra, dec, radius_arcsec):
    """Per position the index of the nearest catalogue star within the radius, else -1."""
    from astropy.coordinates import SkyCoord

    if len(ra) == 0:
        return [-1] * len(sky)
    sep = sky[:, None].separation(SkyCoord(ra, dec, unit="deg")[None, :]).arcsec
    best = np.argmin(sep, axis=1)
    return [int(b) if sep[k, b] <= radius_arcsec else -1 for k, b in enumerate(best)]


def known_columns(result, stars):
    """KNOWN's columns for the given stars from result["known_variables"] (empty for a star not looked up)."""
    k = result.get("known_variables") or {"star": []}
    at = {s: n for n, s in enumerate(k["star"])}
    return {key: [k[key][at[s]] if s in at else empty for s in stars] for key, empty in KNOWN.items()}
