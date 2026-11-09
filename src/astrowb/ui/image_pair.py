"""The Line tool between two stars (plans/photometry.md PHO-24): when both ends of the line sit on stars, the pair is
measured — separation, position angle, flux ratio and Δmag in apertures of the same size."""

import numpy as np
from PySide6.QtCore import QCoreApplication

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("Ctx", "…") calls


def pair_rows(data, x0, y0, x1, y1, wcs=None):
    """Rows for the Line tool's table, or [] when either end is not on a star (centroid within 3 px, S/N ≥ 5)."""
    from ..io.inspect import pair_measure

    try:
        p = pair_measure(data, (x0, y0), (x1, y1), wcs=wcs.celestial if wcs is not None else None)
    except Exception:  # noqa: BLE001 - an end off the frame or on blank sky: no pair, the line alone
        return []
    on_stars = np.hypot(p["x1"] - x0, p["y1"] - y0) <= 3 and np.hypot(p["x2"] - x1, p["y2"] - y1) <= 3
    if not on_stars or not (p["ratio"] > 0 and p["ratio_err"] < p["ratio"] / 5):
        return []
    rows = [
        (translate("ImagePage", "Pair: separation (px)"), f"{p['separation_px']:.3f}"),
        (translate("ImagePage", "Pair: flux ratio f2/f1"), f"{p['ratio']:.4f} ± {p['ratio_err']:.4f}"),
        (translate("ImagePage", "Pair: Δmag (m2 − m1)"), f"{p['dmag']:.3f} ± {p['dmag_err']:.3f}"),
        (translate("ImagePage", "Pair: aperture, sky ring (px)"), f"{p['r_ap']:.1f}, {p['r_in']:.1f}–{p['r_out']:.1f}"),
    ]
    if "position_angle" in p:
        rows[1:1] = [
            (translate("ImagePage", "Pair: separation (″)"), f"{p['separation_arcsec']:.3f}"),
            (translate("ImagePage", "Pair: position angle (°, N through E)"), f"{p['position_angle']:.2f}"),
        ]
    return rows
