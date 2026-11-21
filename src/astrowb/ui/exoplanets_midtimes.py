"""The Exoplanets window's "Mid-times" result tab (plans/interface.md UI-16.7): each fitted file's mid-transit time and
error in a session list, the linear ephemeris fitted to them (timeseries.ephemeris, epochs from the entered period)
and the O−C against epoch; "Send to O−C" hands the times to the O−C window."""

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ..timeseries import ephemeris
from .kit import tokens
from .kit.table_view import DataTable
from .plot.toolbar import plot_box

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ExoplanetsMidtimes", "…") calls


def midtimes(page):
    """[(file, Tc, σ)] of the fitted files, in the order of the file list."""
    return [(page.sets[i][0], f["values"]["tc"], f["errors"].get("tc", 0.0)) for i, f in sorted(page.fits.items())]


def ephemeris_fit(rows, period):
    """The linear ephemeris of the mid-times, epochs counted from the first one; None until two epochs differ."""
    minima = [ephemeris.Minimum(t, e or None, source=n) for n, t, e in rows]
    if len(rows) < 2 or len(set(ephemeris.epochs(minima, rows[0][1], period))) < 2:
        return None
    return ephemeris.fit(minima, rows[0][1], period)


def oc_figure(f):
    """O−C (minutes) of the mid-times against epoch, with the fitted line."""
    from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec

    ctx = "ExoplanetsMidtimes"
    e = np.asarray(f.epochs, float)
    grid = np.linspace(e.min(), e.max(), 2)
    return FigureSpec([PanelSpec(AxisSpec(translate(ctx, "Epoch")), AxisSpec(translate(ctx, "O−C (min)")), [
        SeriesSpec(translate(ctx, "mid-times"), e, f.o_minus_c * 1440),
        SeriesSpec(translate(ctx, "linear ephemeris"), grid, f.model_o_minus_c(grid) * 1440, kind="line",
                   colour=tokens.role("saturated")),
    ])])  # fmt: skip


def midtimes_dock(win, page):
    box = QWidget(win)
    table, summary = DataTable(box), QLabel(box)
    plot_widget, plot = plot_box(box)
    send = QPushButton(translate("ExoplanetsMidtimes", "Send to O−C"), box)
    send.setToolTip(translate("ExoplanetsMidtimes", "The mid-times of the fitted files, as times of minimum in O−C"))
    lay = QVBoxLayout(box)
    for w in (table, plot_widget, summary, send):
        lay.addWidget(w)
    page.midtimes_table, page.midtimes_plot, page.midtimes_summary, page.midtimes_send = table, plot, summary, send
    send.clicked.connect(lambda: page.midtimes_to_oc.emit(midtimes(page)))
    box.hide()  # docked at the first fit, like the other result tabs
    state, show = {"docked": False}, page.show_fit

    def show_fit(out):
        show(out)
        rows = midtimes(page)
        ctx = "ExoplanetsMidtimes"
        table.set_data([translate(ctx, "File"), translate(ctx, "Tc (BJD)"), translate(ctx, "σ (d)")], rows)
        if not state["docked"]:
            win.add_result_tab("midtimes", translate(ctx, "Mid-times"), box)
            box.show()
            state["docked"] = True
        f = ephemeris_fit(rows, page.period.value())
        if f is None:
            summary.setText(translate(ctx, "Two fits at different epochs give the linear ephemeris."))
            return
        plot.set_figure(oc_figure(f))
        summary.setText(
            translate(ctx, "T0 = {t0:.6f} ± {t0e:.6f} BJD; P = {p:.7f} ± {pe:.7f} d; χ²ᵣ = {chi:.2f}").format(
                t0=f.t0, t0e=f.t0_err, p=f.period, pe=f.period_err, chi=f.chi2r
            )
        )

    page.show_fit = show_fit
