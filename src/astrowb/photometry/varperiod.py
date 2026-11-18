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
