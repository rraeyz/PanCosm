"""The "Periodogram" results tab of the O−C window (plans/oc.md OC-11, OC-6.3): the GLS periodogram of the last fit's
residuals with its highest peak, and "Fit the highest peak as LTTE": the third-body fit searched around that peak."""

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from .kit import tokens
from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("OcPeriodogram", "…") calls
SEED = 1.25  # the third-body search spans peak / SEED … peak × SEED


def errors(minima):
    """The minima's errors, a missing one the median of the others (1 d when none has one), as ephemeris.fit."""
    e = np.array([m.error or np.nan for m in minima], float)
    return np.where(np.isnan(e), np.nanmedian(e) if np.isfinite(e).any() else 1.0, e)


def refresh(page, f, minima):
    from ..timeseries.ltte import residual_periodogram

    page.peak_period = None
    page.peak_button.setEnabled(False)
    try:
        periods, power, best, fap = residual_periodogram([m.time for m in minima], f.residuals, errors(minima))
    except (ValueError, ZeroDivisionError):  # too few minima for a periodogram
        page.periodogram_plot.set_figure(FigureSpec([]))
        page.periodogram_label.setText(translate("OcPeriodogram", "Too few minima for a periodogram."))
        return
    page.peak_period = float(best)
    page.peak_button.setEnabled(True)
    series = [SeriesSpec(translate("OcPeriodogram", "power"), periods, power, kind="line"),
              SeriesSpec(translate("OcPeriodogram", "highest peak"), [best], kind="vline",
                         colour=tokens.role("saturated"))]  # fmt: skip
    page.periodogram_plot.set_figure(
        FigureSpec(
            [
                PanelSpec(
                    AxisSpec(translate("OcPeriodogram", "Period"), "d", scale="log"),
                    AxisSpec(translate("OcPeriodogram", "Power")),
                    series,
                )
            ]
        )  # fmt: skip
    )
    page.periodogram_label.setText(
        translate(
            "OcPeriodogram", "Highest peak of the residuals: {p:.1f} d ({y:.2f} yr), false-alarm probability {fap:.2g}"
        ).format(p=best, y=best / 365.25, fap=fap)  # fmt: skip
    )


def fit_peak(page):
    """The third-body model, its period searched around the highest peak."""
    if page.peak_period:
        page.ltte.setChecked(True)
        page.run_fit(p3_range=(page.peak_period / SEED, page.peak_period * SEED))


def add_periodogram(page):
    """The tab's widget; refreshed after every fit (show_fit wrapped)."""
    from .plot.toolbar import plot_box

    box = QWidget(page)
    plot_widget, page.periodogram_plot = plot_box(box, "oc_periodogram")
    page.periodogram_label = QLabel(box)
    page.periodogram_label.setWordWrap(True)
    page.peak_button = QPushButton(translate("OcPeriodogram", "Fit the highest peak as LTTE"), box)
    page.peak_button.setToolTip(translate(
        "OcPeriodogram", "Fits a third body (light-travel time) with its orbital period searched around the highest "
        "peak of the residuals",
    ))  # fmt: skip
    page.peak_button.setEnabled(False)
    page.peak_button.clicked.connect(lambda: fit_peak(page))
    page.peak_period = None
    box.hide()  # docked at the first fit (oc_stages)
    lay = QVBoxLayout(box)
    for w in (plot_widget, page.periodogram_label, page.peak_button):
        lay.addWidget(w, 1 if w is plot_widget else 0)
    show = page.show_fit

    def show_fit(f, minima):
        out = show(f, minima)
        refresh(page, f, minima)
        return out

    page.show_fit = show_fit
    return box
