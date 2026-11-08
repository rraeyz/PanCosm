"""Shared widgets of the pages: titles, folding sections, the workflow line and the plot canvas."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


def _title(text, parent):
    label = QLabel(f"<h2>{text}</h2>", parent)
    label.setTextFormat(Qt.RichText)
    return label


def glyph(text, color, size=40):
    """A toolbar icon drawn from a symbol of the user interface font, in the text colour of the theme."""
    from PySide6.QtGui import QPainter, QPixmap

    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    font = p.font()
    font.setPixelSize(int(size * 0.8))
    p.setFont(font)
    p.setPen(color)
    p.drawText(pix.rect(), Qt.AlignCenter, text)
    p.end()
    return QIcon(pix)


class _FoldButton(QToolButton):
    """A section title that shortens itself with "…" when the column is narrow (the whole title in the tooltip): a
    long one-line title ("Workflow — next: …") kept a page wider than the window (the owner's Calibrate page)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full = self._tip = ""
        self.setSizePolicy(QSizePolicy.Preferred, self.sizePolicy().verticalPolicy())  # may be narrower than its text

    def setToolTip(self, tip):
        self._tip = tip
        self._fit()

    def text(self):
        return self._full

    def setText(self, text):
        self._full = text
        self._fit()
        self.updateGeometry()

    def _chrome(self):  # the arrow and padding beside the text
        return super().sizeHint().width() - self.fontMetrics().horizontalAdvance(super().text())

    def sizeHint(self):
        size = super().sizeHint()
        size.setWidth(self._chrome() + self.fontMetrics().horizontalAdvance(self._full))
        return size

    def minimumSizeHint(self):
        size = super().minimumSizeHint()
        size.setWidth(self._chrome() + self.fontMetrics().horizontalAdvance("…" + self._full[:12]))
        return size

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def _fit(self):
        room = max(self.width() - self._chrome(), 1) if self.isVisible() else 10**6
        shown = self.fontMetrics().elidedText(self._full, Qt.ElideRight, room)
        QToolButton.setText(self, shown)
        QToolButton.setToolTip(self, self._tip if shown == self._full else f"{self._full}\n\n{self._tip}".strip())


class Collapsible(QWidget):
    """A titled section that opens and closes: options that are rarely changed stay out of the way, the main
    steps stay in sight. Add widgets to .body (a QVBoxLayout)."""

    def __init__(self, title, parent=None, expanded=False, mode="expert"):
        """mode: "expert" — open in Expert mode, folded in Basic mode (options rarely changed); "basic" — the other
        way round (help for a first-time user); None — not touched by the interface mode."""
        super().__init__(parent)
        self.mode = mode
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.button = _FoldButton(self)
        self.button.setText(title)
        self.button.setCheckable(True)
        self.button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.button.setAutoRaise(True)
        self.button.setToolTip(self.tr("Click to show or hide these options"))
        self.content = QWidget(self)
        self.body = QVBoxLayout(self.content)
        self.body.setContentsMargins(18, 0, 0, 0)
        lay.addWidget(self.button)
        lay.addWidget(self.content)
        self.button.toggled.connect(self.set_expanded)
        self.set_expanded(expanded)

    def set_expanded(self, on):
        self.button.setChecked(on)
        self.button.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
        self.content.setVisible(on)


class StepGuide(QWidget):
    """The usual order of work (the IRAF task in brackets), folded into one line that names the next step; opened,
    every step marked done, skipped, next or still to come, and what to do for the next one. A guide, never a lock:
    the owner, "I have a reduced spectrum, I only want the calibration — must I start over?". steps: [(title, what
    to do)]; set_state(i, "done" | "skipped" | None)."""

    def __init__(self, steps, parent=None):
        super().__init__(parent)
        self.steps, self.states = list(steps), [None] * len(steps)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 4)
        self.box = Collapsible("", self, expanded=False, mode=None)
        self.box.button.setToolTip(self.tr("Click to show or hide the usual order of work"))
        note = QLabel(
            self.tr("The usual order, not a rule: start where your data are and skip what they do not need."), self
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: gray")
        self.box.body.addWidget(note)
        self.labels = []
        for _ in self.steps:
            label = QLabel(self)
            label.setWordWrap(True)
            label.setTextFormat(Qt.RichText)
            self.box.body.addWidget(label)
            self.labels.append(label)
        self.now = QLabel(self)
        self.now.setWordWrap(True)
        self.now.setTextFormat(Qt.RichText)
        self.box.body.addWidget(self.now)
        lay.addWidget(self.box)
        self._refresh()

    def set_state(self, i, state="done"):
        self.states[i] = state
        self._refresh()

    def current(self):
        return next((i for i, s in enumerate(self.states) if s is None), None)

    def reset(self):
        self.states = [None] * len(self.steps)
        self._refresh()

    def _refresh(self):
        now = self.current()
        for i, ((title, _), label, st) in enumerate(zip(self.steps, self.labels, self.states, strict=True)):
            mark = {"done": "✓", "skipped": "–"}.get(st, "▶" if i == now else "·")
            text = f"{mark} {i + 1}. {title}"
            label.setText(f"<b>{text}</b>" if i == now else (f"<span style='color:gray'>{text}</span>" if st else text))
        if now is None:
            self.box.button.setText(self.tr("Workflow: all steps done"))
            self.now.setText("")
            return
        title = self.steps[now][0]
        self.box.button.setText(self.tr("Workflow — next: {n}. {step}").format(n=now + 1, step=title))
        self.now.setText("<b>" + self.tr("Next:") + "</b> " + self.steps[now][1])


def _canvas_class():
    """matplotlib's Qt canvas (imported on first use: it is slow to import) that never makes its figure 0 px."""
    global _Canvas
    if "_Canvas" not in globals():
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

        class _Canvas(FigureCanvasQTAgg):
            def resizeEvent(self, event):
                super().resizeEvent(event)
                fig, least = self.figure, 1 / self.figure.dpi
                w, h = fig.get_size_inches()
                if w < least or h < least:  # folded to 0 px: a 0-px axis has no inverse transform, drawing raises
                    fig.set_size_inches(max(w, least), max(h, least), forward=False)

    return _Canvas


class PlotCanvas(QWidget):
    """A matplotlib figure in the window (the same library makes the publication-quality exports)."""

    def __init__(self, parent=None, figure=None):
        super().__init__(parent)
        from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
        from matplotlib.figure import Figure

        self.figure = figure or Figure(figsize=(6, 3), layout="constrained")
        self.canvas = _canvas_class()(self.figure)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        toolbar = NavigationToolbar2QT(self.canvas, self)
        toolbar.addAction(self.tr("Publication figure…"), self.export_publication)
        data = toolbar.addAction(self.tr("Export data (CSV)…"), self.export_data)
        data.setToolTip(self.tr("The numbers of every plotted series (axis, series, x, y) in a CSV file"))
        toolbar.addAction(self.tr("Open in a new window"), self.open_window)
        lay.addWidget(toolbar)
        lay.addWidget(self.canvas)
        self._windows = []

    def draw(self):
        self.canvas.draw_idle()

    def open_window(self):
        """A copy of the plot in its own resizable window, to look at it large while working on."""
        import pickle

        try:
            fig = pickle.loads(pickle.dumps(self.figure))
        except Exception:  # functions in it (axis formatters, secondary axes) cannot be copied: a sharp picture of it
            fig = self._picture_copy()
        dlg = QDialog(self.window())
        dlg.setWindowTitle(self.window().windowTitle() or self.tr("Plot"))
        dlg.setAttribute(Qt.WA_DeleteOnClose)
        lay = QVBoxLayout(dlg)
        lay.addWidget(PlotCanvas(dlg, figure=fig))
        dlg.resize(1100, 700)
        dlg.show()
        self._windows.append(dlg)
        dlg.destroyed.connect(lambda *_: self._windows.remove(dlg) if dlg in self._windows else None)
        return dlg

    def _picture_copy(self):
        """The figure drawn at three times the screen resolution into a new figure, zoomable with the toolbar (the
        Plan chart's time axes are functions: pickling it failed and the window did not open)."""
        import io

        from matplotlib.figure import Figure
        from matplotlib.image import imread

        buf = io.BytesIO()
        self.figure.savefig(buf, format="png", dpi=3 * self.figure.dpi)
        buf.seek(0)
        img = imread(buf)
        fig = Figure(figsize=self.figure.get_size_inches(), layout="constrained")
        ax = fig.add_subplot()
        ax.imshow(img)
        ax.set_axis_off()
        return fig

    def data_rows(self):
        """[(axis, series, x, y)] of every line and point series drawn (scatter points included); the series is its
        legend label, or line / points with a number when it has none."""
        import numpy as np

        rows = []
        for a, ax in enumerate(self.figure.axes, 1):
            name = ax.get_ylabel() or f"axis {a}"
            series = [(ln.get_label(), ln.get_xydata()) for ln in ax.get_lines()]
            series += [(col.get_label(), col.get_offsets()) for col in ax.collections if len(col.get_offsets())]
            for k, (label, xy) in enumerate(series, 1):
                label = label if label and not label.startswith("_") else f"series {k}"
                for x, y in np.asarray(xy, float).reshape(-1, 2):
                    rows.append((name, label, float(x), float(y)))
        return rows

    def export_data(self, path=None):
        import csv

        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, self.tr("Export data"), "plot.csv", "CSV (*.csv)")
            if not path:
                return None
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["axis", "series", "x", "y"])
            w.writerows(self.data_rows())
        return path

    def export_publication(self, path=None):
        """Black on white whatever the screen theme: PDF / SVG / EPS, or PNG at 300 dpi."""
        from .export import save_publication

        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("Publication figure"),
                "figure.pdf",
                "PDF (*.pdf);;PNG, 300 dpi (*.png);;SVG (*.svg);;EPS (*.eps)",
            )
        return save_publication(self.figure, path) if path else None
