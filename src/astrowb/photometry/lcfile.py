"""The light-curve file (plans/photometry.md PHO-48): an ECSV (`.lc.ecsv`) holding the measured light-curve dict
whole — the per-frame series as columns (several values per frame as multidimensional columns), everything else
(radii, the left-out frames, options, provenance) in the header — so that `read` gives back the same dict. `time`,
`flux`, `flux_err` are there under those names too, for Astropy's and lightkurve's generic readers.

VERSION is written in the header; a file without it is an older simple CSV (nights.read_export reads those).
"""

import numpy as np
from astropy.table import Table

VERSION = 1
ALIASES = {"flux": "rel_flux", "flux_err": "rel_flux_err"}


def _column(value, n):
    """The value as a regular numeric or text array of n rows, or None when it is not one."""
    if not isinstance(value, list) or len(value) != n or any(v is None for v in np.ravel(np.array(value, object))):
        return None
    try:
        arr = np.array(value)
    except ValueError:  # ragged
        return None
    return arr if arr.dtype.kind in "fiub" or (arr.dtype.kind == "U" and arr.ndim == 1) else None


def write(lc, path, provenance=None):
    n = len(lc["time"])
    columns, meta = {}, {}
    for key, value in lc.items():
        arr = _column(value, n)
        if arr is None:
            meta[key] = value
        else:
            columns[key] = arr
    t = Table(columns)
    for alias, source in ALIASES.items():
        if source in columns and alias not in columns:
            t[alias] = columns[source]
    if "time" in t.colnames:
        t["time"].unit = "d"
        t["time"].description = f"mid-exposure time, {lc.get('time_scale', 'unknown scale')}"
    t.meta.update({"version": VERSION, "lc": meta, "columns": list(columns), "provenance": provenance or {}})
    t.write(path, format="ascii.ecsv", overwrite=True)
    return path


def read(path):
    """The light-curve dict as it was written (columns back to lists, in their order)."""
    t = Table.read(path, format="ascii.ecsv")
    if t.meta.get("version") != VERSION:
        version = t.meta.get("version")
        raise ValueError(f"not a light-curve file of this version: {version}")
    out = {key: t[key].tolist() for key in t.meta["columns"]}
    out |= dict(t.meta["lc"])
    return out
