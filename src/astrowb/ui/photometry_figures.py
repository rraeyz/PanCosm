"""The Photometry page's bottom plot as FigureSpecs (ARC-6): the light curve views, the frame quality and the radial
profile with the apertures. Plain data in, a figure description out; the page keeps the state and the clicks.
Texts keep the context of the page they belong to."""

import numpy as np
from PySide6.QtCore import QCoreApplication

from .kit import tokens
from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec

translate = QCoreApplication.translate
SERIES = tokens.SERIES
RED, GREY, ORANGE = tokens.role("saturated"), tokens.role("rejected"), tokens.role("non_linear")


def _halo(name, x, y, mask, colour):
    """Points ringed by a larger dot underneath them (a hollow circle has no symbol in the spec)."""
    return SeriesSpec(name, x[mask], y[mask], colour=colour, size=9, z=-1, ids=np.flatnonzero(mask))


def points(name, x, y, ye=None, pickable=True):
    return SeriesSpec(name, x, y, yerr=ye, size=4, alpha=0.8, pickable=pickable)


def light_curve_points(name, x, y, ye, sat, lin, extra=()):
    """The (pickable) points of a light curve with the saturated and non-linear frames ringed and `extra` marks."""
    series = [points(name, x, y, ye)]
    if sat.any():
        series.append(_halo(translate("PhotometryPage", "saturated"), x, y, sat, RED))
    if lin.any():
        series.append(_halo(translate("PhotometryPage", "non-linear"), x, y, lin, ORANGE))
    return [*series, *extra]


def differential(lc, x, y, ye, sat, lin, k, name_k, gap, note):
    """The classic differential plot: Δm of the target (picked), the second curve `k` offset by `gap`, and the note
    about frames without a flux. y is inverted on the page."""
    name = translate("PhotometryPage", "T1 − comparison")
    series = light_curve_points(name, x, y, ye, sat, lin)
    if note:
        series.append(SeriesSpec("note", [np.nanmedian(x)], [np.nanmin(y)], kind="text", labels=[note], colour=RED))
    if k is not None:
        series.append(SeriesSpec(name_k, x, k - gap, size=4, colour=GREY))  # above: axis inverted
    return series


def offset_curves(x, curves, spacing):
    """[(name, values)] one below the other, `spacing` apart."""
    return [SeriesSpec(name, x, np.asarray(c, float) - spacing * i, size=4) for i, (name, c) in enumerate(curves)]


def covariate_curves(x, cov):
    out = []
    for key in ("airmass", "sky", "fwhm", "x", "y"):
        if key in cov:
            v = np.asarray(cov[key], float)
            out.append(SeriesSpec(key, x, (v - np.nanmean(v)) / (np.nanstd(v) or 1), size=3))
    return out


def minima_marks(minima, t_ref):
    """Vertical lines at the timed minima: primary red, secondary orange."""
    out = []
    for kind, colour in (("I", RED), ("II", ORANGE)):
        times = [m["time"] - t_ref for m in minima if m["kind"] == kind]
        if times:
            out.append(SeriesSpec(f"minimum {kind}", times, kind="vline", colour=colour, width=0.8))
    return out


def quality_figure(rows, labels):
    """FWHM, number of stars and sky of every frame, three panels; the bad frames in red."""
    n = np.arange(len(rows))
    bad = np.array([not r["good"] for r in rows])
    panels = []
    for key, label in zip(("fwhm", "stars", "background"), labels, strict=True):
        y = np.array([np.nan if r[key] is None else r[key] for r in rows], float)
        last = key == "background"
        series = [
            SeriesSpec(label, n, y, kind="line", width=0.6),
            SeriesSpec(label, n, y, size=4),
            SeriesSpec(translate("PhotometryPage", "bad frames"), n[bad], y[bad], size=7, colour=RED),
        ]
        panels.append(
            PanelSpec(AxisSpec(translate("PhotometryPage", "Frame") if last else ""), AxisSpec(label), series)
        )
    return FigureSpec(panels)


def aperture_figure(a):
    """The star's radial profile with the aperture, the gap and the sky annulus marked."""
    t = translate
    spans = [
        SeriesSpec(t("PhotometryPage", "aperture"), [0.0], [a["r_ap"]], kind="span", alpha=0.18, colour=SERIES[2]),
        SeriesSpec(t("PhotometryPage", "sky annulus"), [a["r_in"]], [a["r_out"]], kind="span", alpha=0.18,
                   colour=SERIES[5]),
    ]  # fmt: skip
    name = t("PhotometryPage", "star profile (peak = 1)")
    profile = [
        SeriesSpec(name, a["profile_r"], a["profile"], kind="line", width=0.8),
        SeriesSpec(name, a["profile_r"], a["profile"], size=4),
    ]
    guides = [
        SeriesSpec("0", [0.0], kind="hline", width=0.5, colour=GREY),
        SeriesSpec("0.5", [0.5], kind="hline", width=0.5, colour=GREY, dash="dot"),
        SeriesSpec("radii", [a["r_ap"], a["r_in"], a["r_out"]], kind="vline", width=0.8, colour=GREY, dash="dash"),
    ]
    axes = (
        AxisSpec(translate("PhotometryPage", "Radius (px)"), limits=(0, a["r_out"] * 1.15)),
        AxisSpec(translate("PhotometryPage", "Relative brightness")),
    )
    return FigureSpec([PanelSpec(*axes, [*spans, *profile, *guides])])
