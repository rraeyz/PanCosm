"""Multi-plot of a light curve (plans/photometry.md item 8), after AstroImageJ's Multi-Plot (its Y-data rows): several
series on one time axis, each normalised on its own (the whole night, or a time range such as out of eclipse), binned
by a number of points or by minutes, offset one below the other, with its own colour; the set-up saved as a template
and opened on another night (PNG / SVG / PDF and the plotted numbers come from the plot's own toolbar). Also "leave
each comparison star out in turn": the target's scatter with every ensemble less one star, as AstroImageJ's "cycle the
comparison stars less one"."""

import json

import numpy as np

from ..timeseries.fourier import bin_time
from .differential import covariates, ensemble
from .measurements import star_names

QUANTITIES = ("airmass", "sky", "fwhm", "x", "y")
VERSION = 1


def available(lc):
    """The series a light curve offers: rel_flux of T1 and of every further target or check star (against the same
    ensemble), the raw flux of every comparison star, and the per-frame quantities."""
    n_comp = np.asarray(lc.get("comp_flux") or np.zeros((len(lc["time"]), 0)), float).reshape(len(lc["time"]), -1)
    names = star_names(n_comp.shape[1], len(lc.get("extra") or []))
    keys = ["rel_flux_T1"] + [f"rel_flux_{names[1 + n_comp.shape[1] + i]}" for i in range(len(lc.get("extra") or []))]
    keys += [f"Source-Sky_{names[1 + k]}" for k in range(n_comp.shape[1])]
    return keys + [q for q in QUANTITIES if q in covariates(lc)]


def series(lc, key):
    """(values, errors or None) of one series named as available() names it."""
    n_comp = len(lc.get("comp_flux")[0]) if lc.get("comp_flux") else 0
    names = star_names(n_comp, len(lc.get("extra") or []))
    if key == "rel_flux_T1":
        return np.asarray(lc["rel_flux"], float), np.asarray(lc["rel_flux_err"], float)
    if key.startswith("rel_flux_"):
        x = lc["extra"][names.index(key[9:]) - 1 - n_comp]
        return np.asarray(x["rel_flux"], float), np.asarray(x["rel_flux_err"], float)
    if key.startswith("Source-Sky_"):
        k = names.index(key[11:]) - 1
        err = lc.get("comp_flux_err")
        return np.asarray(lc["comp_flux"], float)[:, k], None if err is None else np.asarray(err, float)[:, k]
    if key in QUANTITIES:
        return np.asarray(covariates(lc)[key], float), None
    raise KeyError(key)


def prepare(t, y, err=None, norm=None, bin_n=0, bin_minutes=0.0):
    """One series ready to draw: divided by its median (over norm=(t1, t2) when given, else the whole night; nothing
    when norm is False, as for airmass), then binned by bin_n points or bin_minutes (the mean and its error, from
    bin_time). Returns (t, y, err or None)."""
    t, y = np.asarray(t, float), np.asarray(y, float)
    e = None if err is None else np.asarray(err, float)
    ok = np.isfinite(t) & np.isfinite(y)
    t, y, e = t[ok], y[ok], None if e is None else e[ok]
    if norm is not False and len(y):
        inside = np.ones(len(t), bool) if norm is None else (t >= norm[0]) & (t <= norm[1])
        scale = np.nanmedian(y[inside]) if inside.any() else np.nanmedian(y)
        y = y / scale
        e = None if e is None else e / abs(scale)
    if bin_minutes > 0 and len(t):
        out = bin_time(t, y, bin_minutes / 1440.0, err=e if e is not None else np.zeros_like(y))
        return out[0], out[1], (out[2] if e is not None else None)
    if bin_n > 1 and len(t):
        k = np.arange(len(t)) // int(bin_n)
        n = np.bincount(k)
        tb, yb = np.bincount(k, t) / n, np.bincount(k, y) / n
        if e is None:
            return tb, yb, None
        own = np.sqrt(np.bincount(k, e**2)) / n
        spread = np.sqrt(np.maximum(np.bincount(k, y**2) / n - yb**2, 0) / np.maximum(n - 1, 1))
        return tb, yb, np.where(n > 1, np.maximum(own, spread), own)
    return t, y, e


def point_scatter(y):
    """Point-to-point scatter: std of successive differences / √2, so a slow change (the eclipse itself) does not
    count, only the noise."""
    d = np.diff(np.asarray(y, float)[np.isfinite(y)])
    return float(np.std(d) / np.sqrt(2)) if len(d) > 1 else np.nan


def leave_each_out(lc):
    """[(index of the comparison star left out, or None for the full ensemble; scatter of T1's rel_flux in mmag)] for
    the full ensemble and for every ensemble less one star, best first. A comparison star whose removal lowers the
    scatter much is suspect."""
    comp = np.asarray(lc["comp_flux"], float)
    cerr = np.asarray(lc.get("comp_flux_err") or np.zeros_like(comp), float)
    f = np.asarray(lc["target_flux"], float)
    s = np.asarray(lc.get("target_flux_err") or np.zeros_like(f), float)

    def mmag(cols):
        rel, _ = ensemble(f, s, comp[:, cols], cerr[:, cols])
        return float(1000 * 2.5 / np.log(10) * point_scatter(rel / np.nanmedian(rel)))

    out = [(None, mmag(list(range(comp.shape[1]))))]
    if comp.shape[1] > 1:
        out += [(k, mmag([j for j in range(comp.shape[1]) if j != k])) for k in range(comp.shape[1])]
    return sorted(out, key=lambda r: r[1])


def save_template(path, rows, bin_n=0, bin_minutes=0.0, norm=None, spacing=0.0):
    """rows: [{"key", "colour", "normalise": bool, "offset"}]. Series are kept by name (rel_flux_T1, Source-Sky_C2,
    airmass …), so another night with the same numbering takes the same plot. Times of norm are hours after the
    night's first frame, so they carry over too."""
    doc = {"version": VERSION, "rows": list(rows), "bin_n": int(bin_n), "bin_minutes": float(bin_minutes),
           "norm_hours": None if norm is None else list(map(float, norm)), "spacing": float(spacing)}  # fmt: skip
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    return path


def load_template(path):
    """The template's dict. Raises ValueError for a file that is not a multi-plot template."""
    with open(path, encoding="utf-8") as f:
        try:
            doc = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError("not a multi-plot template") from e
    if not isinstance(doc, dict) or not isinstance(doc.get("rows"), list):
        raise ValueError("not a multi-plot template")
    return doc
