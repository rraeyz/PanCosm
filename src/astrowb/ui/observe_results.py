"""Observing results dock (UI-16.9): Log (the observatory's timeline as text, with a filter line) and Graphs (the
camera temperature and the focuser position over time). Everything comes from the status the page already polls;
values the status does not carry (HFR, guiding, sky, airmass) are not drawn."""

import time

import numpy as np
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget

from .plot.toolbar import plot_box

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ObserveResults", "…") calls
MAX_SAMPLES = 2000


def series():
    """(status key, field, panel title) of the values the status carries."""
    return (("camera", "CCDTemperature", translate("ObserveResults", "Camera temperature")),
            ("focuser", "Position", translate("ObserveResults", "Focuser position")))  # fmt: skip


def filtered(lines, text):
    """The lines containing text (any case); all of them when text is empty."""
    needle = text.strip().lower()
    return [ln for ln in lines if needle in ln.lower()]


def graphs_figure(samples):
    """samples: {title: [(seconds, value)]}; one panel per series that has values, on a shared time axis."""
    from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec

    panels = []
    for title, points in samples.items():
        if points:
            t, v = np.array(points, dtype=float).T
            panels.append(PanelSpec(AxisSpec(translate("ObserveResults", "Time"), "s"), AxisSpec(title),
                                    [SeriesSpec(title, t, v, kind="line")]))  # fmt: skip
    return FigureSpec(panels)


class ObserveResults:
    def __init__(self, win, page):
        self.win, self.page, self.lines, self.t0 = win, page, [], None
        self.samples = {title: [] for _, _, title in series()}
        box = QWidget(win)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        self.filter = QLineEdit(box)
        self.filter.setPlaceholderText(translate("ObserveResults", "Filter the log"))
        self.filter.setClearButtonEnabled(True)
        self.view = QPlainTextEdit(box)
        self.view.setReadOnly(True)
        self.view.setFocusPolicy(Qt.NoFocus)
        lay.addWidget(self.filter)
        lay.addWidget(self.view, 1)
        graphs, self.plot = plot_box(win)
        for w in (*box.findChildren(QWidget), *graphs.findChildren(QWidget)):
            if w is not self.filter:
                w.setFocusPolicy(Qt.NoFocus)  # tabs behind the front one sit off-screen: Tab would jump to them
        self.docks = [("log", translate("ObserveResults", "Log"), box),
                      ("graphs", translate("ObserveResults", "Graphs"), graphs)]  # fmt: skip
        for *_, widget in self.docks:
            widget.hide()  # docked at the first line or sample: hidden docks left a stray tab bar in the Tab order
        self.filter.textChanged.connect(self._show_log)
        page.status_arrived.connect(self.update)

    def update(self, st):
        if "error" in st:
            return
        self.lines = list(st.get("log", []))
        self._show_log()
        now = time.monotonic()
        for key, field, title in series():
            value = st.get(key, {}).get(field)
            if isinstance(value, int | float):
                self.t0 = now if self.t0 is None else self.t0
                points = self.samples[title]
                points.append((now - self.t0, float(value)))
                del points[:-MAX_SAMPLES]
        if any(self.samples.values()):
            self.plot.set_figure(graphs_figure(self.samples))
            self._reveal(self.docks[1])

    def _show_log(self):
        self.view.setPlainText("\n".join(filtered(self.lines, self.filter.text())))
        if self.lines:
            self._reveal(self.docks[0])

    def _reveal(self, dock):
        if isinstance(dock, tuple):  # not docked yet
            i = self.docks.index(dock)
            self.docks[i] = self.win.add_result_tab(*dock)
            dock[2].show()  # hidden by hand above, so docking alone would not show it
            self.docks[i].show()
