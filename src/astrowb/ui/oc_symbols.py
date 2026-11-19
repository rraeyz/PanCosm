"""The O−C points of the diagram, one series per (kind, method) present (plans/interface.md UI-16.5): primary and
secondary keep their own symbols; visual and photographic minima get others, CCD, photoelectric and unstated ones the
usual. With no method in any row the series are just primary and secondary."""

import numpy as np
from PySide6.QtCore import QCoreApplication

from .plot.spec import SeriesSpec

translate = QCoreApplication.translate

# symbols (primary, secondary) by method; CCD, pe and None share the first pair
SYMBOLS = {"vis": ("+", "x"), "pg": ("d", "^")}
USUAL = ("o", "s")


def point_series(f, errs, prim, methods, times=None):
    """SeriesSpec of the O−C points; `errs` in minutes, `methods` one code or None per minimum (or None: no methods);
    `times` makes the points pickable with the minimum's time as id (oc_point_select)."""
    methods = np.array([m or "" for m in methods] if methods is not None else [""] * len(prim), dtype=object)
    named = bool((methods != "").any())
    out = []
    for method in dict.fromkeys(methods) if named else [""]:
        for kind_sel, label, i in (
            (prim, translate("OCPage", "primary"), 0),
            (~prim, translate("OCPage", "secondary"), 1),
        ):
            sel = kind_sel & (methods == method) if named else kind_sel
            if sel.any():
                name = f"{label} · {method}" if method else label
                out.append(SeriesSpec(name, f.epochs[sel], f.o_minus_c[sel] * 1440, yerr=errs[sel],
                                      symbol=(SYMBOLS.get(method, USUAL))[i],
                                      pickable=times is not None,
                                      ids=None if times is None else np.asarray(times)[sel]))  # fmt: skip
    return out
