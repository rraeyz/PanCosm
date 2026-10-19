"""Shared widgets of the pages: titles, folding sections, the workflow line and the plot canvas."""

from PySide6.QtCore import QSize, Qt
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


def bar_menu(bar, title):
    """bar.addMenu(title) with the menu made here, parented to the bar: with PySide6 6.8 (the newest that installs on
    the ARM Linux build machine, glibc 2.35) a menu bar's menu made from a title was deleted once QAction.menu() had
    been called on its action and Python collected garbage — the Images window then stopped at start-up ("QMenu
    already deleted"). Submenus (QMenu.addMenu) are not affected."""
    from PySide6.QtWidgets import QMenu

    menu = QMenu(title, bar)
    bar.addMenu(menu)
    return menu


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
        toolbar.setIconSize(QSize(20, 20))  # as the Images toolbar: 24 px cut it in narrow side panels (macOS)
        publication = toolbar.addAction(self.tr("Publication figure…"), self.export_publication)
        data = toolbar.addAction(self.tr("Export data (CSV)…"), self.export_data)
        data.setToolTip(self.tr("The numbers of every plotted series (axis, series, x, y) in a CSV file"))
        window = toolbar.addAction(self.tr("Open in a new window"), self.open_window)
        from .icons import icon

        # icons with their names as tooltips (as the plot's own buttons): the three names cut the toolbar in a
        # narrow side panel (Remote sensing at 1366 px); shortcut: painted once, not again on a theme change
        for act, kind in ((publication, "publication"), (data, "export"), (window, "new_window")):
            act.setIcon(icon(kind, toolbar))
            if act is not data:
                act.setToolTip(act.text())
        lay.addWidget(toolbar)
        lay.addWidget(self.canvas)
        self._windows = []
        # said over the empty plot until something is drawn (UI-6: no blank rectangle without words); a page
        # sets its own words with set_empty_hint
        self._empty_text = self.tr("Nothing to show yet: the plot appears here once there are results")
        self.hint = QLabel(self._empty_text, self.canvas)
        self.hint.setWordWrap(True)
        self.hint.setAlignment(Qt.AlignCenter)
        self.hint.setProperty("muted", True)
        self.hint.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.canvas.mpl_connect("draw_event", lambda _e: (self._update_hint(), self._pickable_legends()))
        self.canvas.mpl_connect("pick_event", self._legend_picked)
        # a: show all (UI-12's plot key; matplotlib's own keys stay: o zoom box, p pan, h home)
        self.canvas.mpl_connect("key_press_event", lambda e: e.key == "a" and self.show_all())
        self._update_hint()
        self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)  # the same right-click menu on every plot (UI-10)
        self.canvas.customContextMenuRequested.connect(self._context_menu)

    def set_empty_hint(self, text):
        self._empty_text = text
        self.hint.setText(text)
        self._update_hint()

    def _pickable_legends(self):
        """A click on a legend entry hides or shows its series (UI-10), on every plot."""
        self._legend_map = {}
        for ax in self.figure.axes:
            legend = ax.get_legend()
            if legend is None:
                continue
            series = {a.get_label(): a for a in [*ax.get_lines(), *ax.collections]}
            for handle, text in zip(legend.legend_handles, legend.get_texts(), strict=False):
                target = series.get(text.get_text())
                if target is not None and handle is not None:
                    handle.set_picker(5)
                    self._legend_map[handle] = (target, text)

    def _legend_picked(self, event):
        hit = getattr(self, "_legend_map", {}).get(event.artist)
        if hit is None:
            return
        target, text = hit
        target.set_visible(not target.get_visible())
        event.artist.set_alpha(1.0 if target.get_visible() else 0.25)
        text.set_alpha(1.0 if target.get_visible() else 0.4)
        self.canvas.draw_idle()

    def set_busy(self, text):
        """UI-6's loading state: while the window's task runs, an empty plot says so (None: back to its hint)."""
        self.hint.setText(text or getattr(self, "_empty_text", self.hint.text()))

    def is_empty(self):
        return not any(
            ax.lines or ax.collections or ax.images or ax.patches or ax.texts or ax.containers
            for ax in self.figure.axes
        )

    def _update_hint(self):
        empty = self.is_empty()
        self.hint.setVisible(empty)
        if empty:
            self.hint.setGeometry(self.canvas.rect().adjusted(24, 24, -24, -24))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_hint()

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

    def _context_menu(self, pos):
        self.context_menu().exec(self.canvas.mapToGlobal(pos))

    def context_menu(self):
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        menu.addAction(self.tr("Show all"), self.show_all)
        menu.addSeparator()
        menu.addAction(self.tr("Copy picture"), self.copy_picture)
        menu.addAction(self.tr("Copy data"), self.copy_data).setEnabled(not self.is_empty())
        # lambdas: the action's "checked" flag must not arrive as the file name
        menu.addAction(self.tr("Save data…"), lambda: self.export_data()).setEnabled(not self.is_empty())
        menu.addAction(self.tr("Publication figure…"), lambda: self.export_publication())
        return menu

    def show_all(self):
        """Every axis back to its data's full range (after zooming)."""
        for ax in self.figure.axes:
            ax.relim()
            ax.autoscale()
        self.canvas.draw_idle()

    def copy_picture(self):
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setPixmap(self.canvas.grab())

    def copy_data(self):
        """Tab-separated axis, series, x, y: pastes into a spreadsheet."""
        from PySide6.QtWidgets import QApplication

        lines = ["axis\tseries\tx\ty"] + ["\t".join(str(v) for v in row) for row in self.data_rows()]
        QApplication.clipboard().setText("\n".join(lines))
        return len(lines) - 1

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
        from ..plot.export import save_publication

        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self,
                self.tr("Publication figure"),
                "figure.pdf",
                "PDF (*.pdf);;PNG, 300 dpi (*.png);;SVG (*.svg);;EPS (*.eps)",
            )
        return save_publication(self.figure, path) if path else None
