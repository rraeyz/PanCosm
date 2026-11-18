"""A table of radial velocities (CSV or text: time and velocity columns, a second star's too) opened in the
Spectroscopy window's Radial velocity tab, for an orbit fit without the spectra (ARC-21's practice file sb2.csv,
or velocities measured elsewhere)."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import QCoreApplication

TIME = ("time", "bjd", "hjd", "jd", "bjd_tdb")
RV1, RV2 = ("rv", "rv1", "v", "v1", "velocity"), ("rv2", "v2")
SCALES = {"bjd": "BJD_TDB", "bjd_tdb": "BJD_TDB", "hjd": "HJD", "jd": "JD"}
ERR1, ERR2 = ("rv_err", "err", "error", "rv1_err", "err1", "e1"), ("rv2_err", "err2", "error2", "e2")


def read(path):
    """The velocity tab's rows of a table with named columns (case does not matter); a missing error column gives
    1 km/s to every point (equal weights)."""
    from astropy.table import Table

    t = Table.read(path, format="ascii")
    cols = {c.lower(): c for c in t.colnames}

    def pick(names):
        name = next((cols[n] for n in names if n in cols), None)
        return None if name is None else np.asarray(t[name], float)

    time, v1 = pick(TIME), pick(RV1)
    # the column's own name is the only scale evidence; a plain "time" stays unknown
    scale = next((SCALES.get(n, "") for n in TIME if n in cols), "")
    if time is None or v1 is None:
        raise ValueError("a velocity table needs a time column and a velocity column (e.g. time, rv1, rv2)")
    v2, e1, e2 = pick(RV2), pick(ERR1), pick(ERR2)
    name = Path(path).name
    rows = []
    for i in range(len(time)):
        row = {"file": f"{name}:{i + 1}", "bjd": float(time[i]), "time_scale": scale, "rv": float(v1[i]),
               "rv_obs": float(v1[i]), "rv_err": float(e1[i]) if e1 is not None else 1.0, "v_corr": 0.0}  # fmt: skip
        if v2 is not None:
            row |= {"rv2": float(v2[i]), "rv2_obs": float(v2[i]), "rv2_err": float(e2[i]) if e2 is not None else 1.0}
        rows.append(row)
    return rows


def scales(rows):
    """The distinct time scales of the rows (rows measured from spectra are barycentric BJD_TDB)."""
    return sorted({r.get("time_scale", "BJD_TDB") for r in rows})


def time_header(rows):
    """The time column's header: the scale when all rows share a known one, else a neutral name."""
    s = scales(rows)
    return s[0] if len(s) == 1 and s[0] else QCoreApplication.translate("VelocityTab", "Time (as in the files)")


def mixed_note(rows):
    """A warning line when the rows' times are on different (or unknown) scales, else an empty string."""
    s = scales(rows)
    if len(s) < 2:
        return ""
    names = ", ".join(x or QCoreApplication.translate("VelocityTab", "unknown") for x in s)
    return QCoreApplication.translate(
        "VelocityTab", "The times mix scales ({s}): convert them before fitting an orbit."
    ).format(s=names)


def open_dialog(tab, path=None):
    """Velocity → Open a velocity table…: the rows replace the measured ones; Fit orbit then works on them."""
    if path is None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getOpenFileName(
            tab, QCoreApplication.translate("MainWindow", "Open a velocity table"), "", "Tables (*.csv *.txt *.dat)"
        )
        if not path:
            return None
    try:
        rows = read(path)
    except (ValueError, OSError) as e:
        from .messages import translate

        tab.status.setText(translate(str(e)))
        return None
    tab.show_rvs(rows)
    return rows
