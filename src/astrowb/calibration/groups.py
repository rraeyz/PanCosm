"""The night's frames in groups, as MaxIm DL's calibration groups and IRAF's ccdgroups show them (plans/calibration.md
CAL-1): one group per type, filter, exposure, binning, read-out settings, temperature (within the tolerance) and
night, with a quick look at every frame (the central 512 × 512) and the frames that stand apart marked with why.

    gs = group(frames)                   [{"kind", "filter", "exptime", "binning", "readout", "temperature", "night",
                                           "paths", "count"}]
    st = stats(path)                     {"median", "noise", "min", "max", "saturated"} of the central part
    marks = outliers(group, saturation)  {path: reason} — level or noise off the group, a flat outside 20–80 %
"""

from pathlib import Path

import numpy as np

_CACHE = {}


def _night(frame):
    from .nights import _night as night_of

    return night_of(frame) or "undated"


def group(frames, temp_tol=2.0):
    """Groups of frame dicts (calibration.scan's), largest first within each kind."""
    out = {}
    for f in frames:
        t = f.get("temperature")
        t_key = None if t is None else round(float(t) / temp_tol) * temp_tol
        exp = f.get("exptime")
        key = (f["kind"], f.get("filter") or "", None if exp is None else round(float(exp), 3),
               tuple(f.get("binning") or (1, 1)), f.get("readout") or "", t_key, _night(f))  # fmt: skip
        g = out.setdefault(key, {"kind": key[0], "filter": key[1], "exptime": key[2], "binning": list(key[3]),
                                 "readout": key[4], "temperature": key[5], "night": key[6], "paths": []})  # fmt: skip
        g["paths"].append(f["path"])
    groups = sorted(out.values(), key=lambda g: (["bias", "dark", "flat", "light"].index(g["kind"])
                                                 if g["kind"] in ("bias", "dark", "flat", "light") else 9,
                                                 -len(g["paths"])))  # fmt: skip
    for g in groups:
        g["count"] = len(g["paths"])
    return groups


def stats(path, size=512):
    """Median, robust noise, minimum, maximum and the share at the top value of the frame's central part (cached by
    path and modification time)."""
    from .masters import load

    p = Path(path)
    key = (str(p), p.stat().st_mtime)
    if key in _CACHE:
        return _CACHE[key]
    data = load(p)[0]
    ny, nx = data.shape
    cy, cx, h = ny // 2, nx // 2, size // 2
    cut = np.asarray(data[max(0, cy - h) : cy + h, max(0, cx - h) : cx + h], float)
    med = float(np.nanmedian(cut))
    top = float(np.nanmax(cut))
    out = {"median": med, "noise": float(1.4826 * np.nanmedian(np.abs(cut - med))), "min": float(np.nanmin(cut)),
           "max": top, "saturated": float(np.mean(cut >= top)) if top > med else 0.0}  # fmt: skip
    _CACHE[key] = out
    return out


def outliers(g, saturation=65535.0, nsigma=5.0):
    """{path: reason} for the frames of a group that stand apart: level or noise beyond nsigma robust σ of the
    group's, a flat outside 20–80 % of saturation."""
    s = {p: stats(p) for p in g["paths"]}
    marks = {}
    for name in ("median", "noise"):
        v = np.array([x[name] for x in s.values()])
        if len(v) >= 3:
            med = np.median(v)
            spread = 1.4826 * np.median(np.abs(v - med))
            for p, x in s.items():
                if abs(x[name] - med) > nsigma * max(spread, 1e-6 * abs(med) + 1e-9):
                    what = "level" if name == "median" else "noise"
                    marks[p] = f"its {what} ({x[name]:.0f}) is far from the group's ({med:.0f})"
    if g["kind"] == "flat":
        for p, x in s.items():
            share = x["median"] / saturation
            if not 0.2 <= share <= 0.8:
                marks[p] = f"a flat at {share:.0%} of saturation (20–80 % advised)"
    return marks
