"""The Images page's graph under the image as FigureSpecs (ARC-6): a star's profile, a rectangle's histogram or
row / column profile, a line's profile. The 3-D surface has no spec and stays on a PlotCanvas (image_page.py)."""

import numpy as np
from PySide6.QtCore import QCoreApplication

from .kit import tokens
from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec

translate = QCoreApplication.translate


def _one(labels, series, log_y=False):
    return FigureSpec([PanelSpec(AxisSpec(labels[0]), AxisSpec(labels[1], scale="log" if log_y else "linear"), series)])


def star_profile_figure(s, labels):
    """Every pixel's counts against its radius (faint), their binned mean, the aperture and the sky annulus."""
    prof = s["profile"]
    centres, binned = prof["bins"]
    series = [
        SeriesSpec(translate("ImagePage", "pixels"), prof["r"], prof["v"], size=2, alpha=0.4),
        SeriesSpec(translate("ImagePage", "binned"), centres, binned, kind="line", width=0.8),
        SeriesSpec(translate("ImagePage", "binned"), centres, binned, size=4),
        SeriesSpec("aperture", [0.0], [s["r_ap"]], kind="span", alpha=0.18, colour=tokens.SERIES[2]),
        SeriesSpec("sky annulus", [s["r_in"]], [s["r_out"]], kind="span", alpha=0.18, colour=tokens.SERIES[5]),
    ]
    return _one(labels, series)


def histogram_figure(h, labels):
    """Pixel counts of a rectangle, log y."""
    return _one(labels, [SeriesSpec(labels[1], h["edges"], h["counts"], kind="histogram", alpha=0.6)], log_y=True)


def profile_figure(x, y, labels):
    return _one(labels, [SeriesSpec(labels[1], np.asarray(x, float), np.asarray(y, float), kind="line", width=0.9)])
