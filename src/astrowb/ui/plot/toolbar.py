"""The toolbar of a PlotView (ARC-6 item 6): show all, box zoom, select range, measure, pick, export…,
publication figure…, open in a window. Its mode buttons set PlotView.base_mode, the same modes the Z / R keys
give while held."""

from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QButtonGroup, QFileDialog, QHBoxLayout, QMessageBox, QVBoxLayout, QWidget

from ..kit.buttons import ToolButton
from ..kit.focus import read_in_order
from . import publish

translate = QCoreApplication.translate
_FILES = "PDF (*.pdf);;PNG (*.png);;SVG (*.svg);;EPS (*.eps)"


class PlotToolbar(QWidget):
    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.view, self.windows = view, []
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)
        self.modes = QButtonGroup(self)  # exclusive: one of pick (pan), box zoom, select range
        self.mode_buttons = {}
        for mode, kind, text in (
            ("pan", "centre", translate("PlotToolbar", "Pick")),
            ("zoom", "zoom_in", translate("PlotToolbar", "Box zoom")),
            ("range", "measure", translate("PlotToolbar", "Select range")),
            ("measure", "radii", translate("PlotToolbar", "Measure (Δx, Δy between two clicks)")),
        ):
            button = ToolButton(kind, text, checkable=True, parent=self)
            button.setChecked(mode == "pan")
            button.toggled.connect(lambda on, m=mode: on and self.set_mode(m))
            self.modes.addButton(button)
            self.mode_buttons[mode] = button
            row.addWidget(button)
        for kind, text, action in (
            ("fit", translate("PlotToolbar", "Show all"), view.show_all),
            ("export", translate("PlotToolbar", "Export data…"), lambda: self.export_data()),
            ("publication", translate("PlotToolbar", "Publication figure…"), lambda: self.export_publication()),
            ("new_window", translate("PlotToolbar", "Open in a window"), self.pop_out),
        ):
            button = ToolButton(kind, text, parent=self)
            button.clicked.connect(action)
            row.addWidget(button)
        row.addStretch(1)
        read_in_order(self, view)  # the plot is made before its toolbar: Tab would reach it first

    def set_mode(self, mode):
        self.view.base_mode = self.view.mode = mode
        self.mode_buttons[mode].setChecked(True)  # when a page sets the mode itself

    def export_data(self, path=None):
        """The plotted numbers as ECSV (publish.data_behind)."""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self, translate("PlotToolbar", "Export data"), "plot.ecsv", "ECSV (*.ecsv)"
            )
        return self._write(publish.data_behind, path)

    def export_publication(self, path=None):
        """PDF / PNG / SVG / EPS by the file's ending (AAS style, single column)."""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self, translate("PlotToolbar", "Publication figure"), "figure.pdf", _FILES
            )
        if path and Path(path).suffix.lower() not in (".pdf", ".png", ".svg", ".eps"):
            path += ".pdf"
        return self._write(publish.publish, path)

    def _write(self, writer, path):
        if not path or self.view.figure is None:  # cancelled, or nothing plotted yet
            return None
        try:
            return str(writer(self.view.figure, path))
        except OSError as e:  # a folder that cannot be written: say so, never crash
            QMessageBox.warning(self, translate("PlotToolbar", "Plot"), str(e))
            return None

    def pop_out(self):
        """The plot as it is now, in its own window with its own toolbar."""
        from .view import PlotView

        window = QWidget()
        window.setWindowTitle(getattr(self.view.figure, "title", None) or translate("PlotToolbar", "Plot"))
        column = QVBoxLayout(window)
        copy = PlotView(self.view.figure, window)
        column.addWidget(PlotToolbar(copy, window))
        column.addWidget(copy)
        window.resize(900, 600)
        window.show()
        self.windows.append(window)
        return window


def plot_box(parent):
    """(a widget holding a PlotToolbar above a PlotView, the PlotView): what a page puts where its plot goes."""
    from .view import PlotView

    box, view = QWidget(parent), PlotView(parent=parent)
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(PlotToolbar(view, box))
    lay.addWidget(view, 1)
    return box, view
