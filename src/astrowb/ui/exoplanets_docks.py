"""The Exoplanets window's result tabs Chains, Corner and Report (plans/interface.md UI-16.7): the MCMC chains of
each parameter, the posterior corner plot, and the fit text with the convergence of every parameter (R̂ and ESS)."""

import numpy as np
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from . import photometry_transit as transit
from .empty_texts import empty_text
from .kit import tokens
from .kit.widgets import PlotCanvas
from .plot.toolbar import plot_box

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ExoplanetsWindow", "…") calls
RHAT_MAX, ESS_MIN = 1.01, 400


def convergence_lines(m):
    """One line per parameter (R̂, ESS) and a warning line when R̂ > 1.01 or ESS < 400 anywhere; [] without chains."""
    if not m or "rhat" not in m:
        return []
    lines = [translate("ExoplanetsWindow", "{name}: R-hat {rhat:.3f}, ESS {ess:.0f}").format(
        name=n, rhat=m["rhat"][n], ess=m["ess_bulk"][n]) for n in m["names"]]  # fmt: skip
    bad = [n for n in m["names"] if m["rhat"][n] > RHAT_MAX or m["ess_bulk"][n] < ESS_MIN]
    if bad:
        lines.append(translate("ExoplanetsWindow", "Warning: not converged ({names}); R-hat > 1.01 or ESS < 400: "
                               "run more MCMC steps.").format(names=", ".join(bad)))  # fmt: skip
    return lines


def report_text(out):
    return "\n".join([transit.result_text(out), "", *convergence_lines(out.get("mcmc"))]).strip()


def chains_figure(m):
    from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec

    c = np.asarray(m["chains"])  # [walker][draw][param]
    x = AxisSpec(translate("ExoplanetsWindow", "Draw"))
    return FigureSpec([PanelSpec(x, AxisSpec(n), [SeriesSpec(f"{n} {w}", np.arange(c.shape[1]), c[w, :, j],
                                                             kind="line", width=0.6, alpha=0.5,
                                                             colour=tokens.role("saturated"))
                                                  for w in range(c.shape[0])])
                       for j, n in enumerate(m["names"])])  # fmt: skip


def draw_corner(figure, m):
    figure.clear()
    if m:
        from .corner import draw_corner as corner

        corner(figure, m["chains"], m["names"])


def exoplanets_docks(win, page):
    chains_box, chains_plot = plot_box(win, "chains")
    corner = PlotCanvas(win)
    corner.set_empty_hint(empty_text("corner"))
    report = QWidget(win)
    text, copy = QPlainTextEdit(report), QPushButton(translate("ExoplanetsWindow", "Copy"), report)
    text.setReadOnly(True)
    copy.clicked.connect(lambda: QApplication.clipboard().setText(text.toPlainText()))
    lay = QVBoxLayout(report)
    lay.addWidget(text)
    lay.addWidget(copy)
    page.chains_plot, page.corner_canvas, page.report_view, page.report_copy = chains_plot, corner, text, copy
    for w in (*chains_box.findChildren(QWidget), *corner.findChildren(QWidget), *report.findChildren(QWidget)):
        w.setFocusPolicy(Qt.NoFocus)  # tabs behind the front one sit off-screen: Tab would jump back up to them
    tabs = [("chains", translate("ExoplanetsWindow", "Chains"), chains_box),
            ("corner", translate("ExoplanetsWindow", "Corner"), corner),
            ("report", translate("ExoplanetsWindow", "Report"), report)]  # fmt: skip
    for *_, widget in tabs:
        widget.hide()  # docked at the first fit: empty docks squeezed the main view, hidden ones left a stray tab bar
    show = page.show_fit

    def show_fit(out):
        show(out)
        out = out.get("transit", out)
        m = out.get("mcmc") if "chains" in (out.get("mcmc") or {}) else None
        while tabs:
            key, title, widget = tabs.pop(0)
            win.add_result_tab(key, title, widget)
            widget.show()  # hidden by hand above, so docking alone would not show it
        if m:
            chains_plot.set_figure(chains_figure(m))
        draw_corner(corner.figure, m)
        corner.canvas.draw_idle()
        text.setPlainText(report_text(out))

    page.show_fit = show_fit
