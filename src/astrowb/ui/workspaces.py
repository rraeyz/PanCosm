"""Workspaces: one page per stage of the work, chosen from the sidebar.

The sidebar follows the workflow (plan -> observe -> calibrate -> measure -> analyse), so a
user always knows where a feature lives. A page only shows the steps of its own job.
"""

import re
from pathlib import Path

import numpy as np
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..brand import BRAND
from ..calibration.frames import Frame
from ..calibration.matching import make_plan
from .messages import translate
from .undo import Undoable
from .viewer import ImageViewer


def _title(text, parent):
    label = QLabel(f"<h2>{text}</h2>", parent)
    label.setTextFormat(Qt.RichText)
    return label


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
        self.button = QToolButton(self)
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


class StartPage(QWidget):
    """Entry points: the user starts from whatever data they already have."""

    action = Signal(str)  # "new_project" | "open_project" | "open_fits" | workspace key
    mode_chosen = Signal(str)  # "basic" | "expert"

    def __init__(self, parent=None, mode="basic"):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.addWidget(_title(self.tr("Welcome to {app}").format(app=BRAND.display_name), self))
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Interface:"), self))
        self.basic = QRadioButton(self.tr("Basic — the main steps; the rarely changed options folded"), self)
        self.expert = QRadioButton(self.tr("Expert — every option open"), self)
        tip = self.tr(
            "Nothing is removed in Basic mode: the folded sections open with one click. Change it here or in the "
            "Settings menu at any time."
        )
        for b, key in ((self.basic, "basic"), (self.expert, "expert")):
            b.setToolTip(tip)
            b.toggled.connect(lambda on, k=key: self.mode_chosen.emit(k) if on else None)
            row.addWidget(b)
        row.addStretch(1)
        (self.expert if mode == "expert" else self.basic).setChecked(True)
        lay.addLayout(row)
        lay.addWidget(QLabel(self.tr("Start from what you have:"), self))
        grid = QGridLayout()
        entries = [
            (self.tr("New project"), self.tr("Keep frames, settings and results together"), "new_project"),
            (self.tr("Open project…"), self.tr("Continue earlier work"), "open_project"),
            (self.tr("Open a FITS image"), self.tr("Look at an image and its header"), "open_fits"),
            (self.tr("I have raw frames"), self.tr("Calibrate with bias, dark and flat"), "calibrate"),
            (self.tr("I have calibrated images"), self.tr("Measure brightness of stars"), "photometry"),
            (self.tr("I have spectra"), self.tr("Reduce spectra, measure radial velocities"), "spectroscopy"),
            (self.tr("I have minima or RV lists"), self.tr("O-C diagrams, orbits"), "timeseries"),
            (self.tr("I want to plan a night"), self.tr("Visibility, airmass, targets"), "plan"),
        ]
        for i, (title, hint, key) in enumerate(entries):
            button = QPushButton(f"{title}\n{hint}", self)
            button.setMinimumHeight(56)
            button.setObjectName(f"start_{key}")
            button.setToolTip(hint)
            button.clicked.connect(lambda _=False, k=key: self.action.emit(k))
            grid.addWidget(button, i // 2, i % 2)
        lay.addLayout(grid)
        lay.addStretch(1)


class ImagePage(Undoable, QWidget):
    """Image viewer with its FITS header and the measuring tools of an image-information window: a star's counts
    in an aperture, the counts in a rectangle, the pixels along a line, with their graphs."""

    TOOLS = ("pan", "aperture", "area", "line")
    header_save_requested = Signal(dict, list)  # {key: [value, comment]}, [deleted keys]
    image_chosen = Signal(str)  # a file picked in the list of open images

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_undo()
        from PySide6.QtWidgets import QButtonGroup

        self.header, self.wcs, self.graph, self._graph_data, self._area = None, None, None, None, None
        self.header_set, self.header_delete = {}, []
        self.viewer = ImageViewer(self)
        left = QWidget(self)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.toolbar = bar = QToolBar(self)  # the main window puts its most used commands in front of the tools
        bar.setIconSize(QSize(20, 20))
        names = {
            "pan": (self.tr("Move"), self.tr("Drag to move the image, wheel to zoom")),
            "aperture": (
                self.tr("Star"),
                self.tr("Click a star: counts in an aperture, background, signal-to-noise, FWHM, HFD, shape"),
            ),
            "area": (self.tr("Area"), self.tr("Drag a rectangle: pixel count, sum, mean, median, std, min, max")),
            "line": (self.tr("Line"), self.tr("Drag a line: pixel values along it, length and angle")),
        }
        self.tool_group = QButtonGroup(self)
        self.tool_buttons = {}
        for key in self.TOOLS:
            b = QToolButton(self)
            b.setText(names[key][0])
            b.setToolTip(names[key][1])
            b.setCheckable(True)
            b.setChecked(key == "pan")
            b.clicked.connect(lambda _=False, k=key: self.set_tool(k))
            self.tool_group.addButton(b)
            self.tool_buttons[key] = b
            bar.addWidget(b)
        ll.addWidget(bar)
        bar = QToolBar(self)  # settings on a second row; a narrow page (a panel beside it) folds them under »
        bar.addWidget(QLabel(self.tr("Aperture radius (px)"), self))
        self.radius = QDoubleSpinBox(self)
        self.radius.setRange(0, 200)
        self.radius.setSingleStep(0.5)
        self.radius.setSpecialValueText(self.tr("from the star"))
        self.radius.setToolTip(self.tr("0: aperture and sky annulus chosen from the star's profile"))
        bar.addWidget(self.radius)
        bar.addWidget(QLabel(self.tr("Line width (px)"), self))
        self.line_width = QDoubleSpinBox(self)
        self.line_width.setRange(1, 101)
        self.line_width.setDecimals(0)
        self.line_width.setToolTip(
            self.tr("Pixels across the line that are averaged for its profile; wider is less noisy")
        )
        bar.addWidget(self.line_width)
        whole = QPushButton(self.tr("Whole image"), self)
        whole.setToolTip(self.tr("Statistics and histogram of the whole image"))
        whole.clicked.connect(self.measure_whole)
        bar.addWidget(whole)
        ll.addWidget(bar)
        self.open_list = QListWidget(self)  # the open images, as MaxIm DL's image windows; only the shown one is read
        self.open_list.setIconSize(QSize(56, 56))
        self.open_list.setToolTip(self.tr("Open images: click one or use the arrow keys to show it"))
        self.open_list.currentRowChanged.connect(self._list_row)
        self.open_list.hide()
        self._thumbs = QTimer(self)
        self._thumbs.setSingleShot(True)
        self._thumbs.timeout.connect(self._next_thumbnail)
        images = QSplitter(Qt.Horizontal, self)
        images.addWidget(self.open_list)
        images.addWidget(self.viewer)
        images.setStretchFactor(1, 1)
        images.setSizes([170, 700])
        ll.addWidget(images, 1)
        self.viewer.clicked.connect(self._clicked)
        self.viewer.region_selected.connect(self.measure_area)
        self.viewer.line_selected.connect(self.measure_line)

        self.header_table = QTableWidget(0, 3, self)
        self.header_table.setHorizontalHeaderLabels([self.tr("Keyword"), self.tr("Value"), self.tr("Comment")])
        self.header_table.horizontalHeader().setStretchLastSection(True)
        self.header_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.info = QTableWidget(0, 2, self)
        self.info.setHorizontalHeaderLabels([self.tr("Quantity"), self.tr("Value")])
        self.info.horizontalHeader().setStretchLastSection(True)
        self.info.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.info.verticalHeader().hide()
        self.info.setEditTriggers(QTableWidget.NoEditTriggers)
        self.graph_tab = QWidget(self)
        gl = QVBoxLayout(self.graph_tab)
        row = QHBoxLayout()
        self.graph_kind = QComboBox(self)
        for key, text in (
            ("histogram", self.tr("Histogram")),
            ("row", self.tr("Profile along x (column means)")),
            ("column", self.tr("Profile along y (row means)")),
            ("surface", self.tr("3-D surface")),
        ):
            self.graph_kind.addItem(text, key)
        self.graph_kind.setToolTip(self.tr("What to draw for a rectangle"))
        self.graph_kind.currentIndexChanged.connect(self._redraw_area)
        self.graph_kind.hide()
        row.addWidget(self.graph_kind, 1)
        export = QPushButton(self.tr("Export data (CSV)…"), self)
        export.clicked.connect(lambda: self.export_graph())
        export.setToolTip(self.tr("The numbers of the graph shown, as a table for a spreadsheet"))
        export.setMinimumWidth(export.sizeHint().width())  # the narrow side panel cut the longer translations
        row.addWidget(export)
        gl.addLayout(row)
        self.tabs = QTabWidget(self)
        header_tab = QWidget(self)
        hl = QVBoxLayout(header_tab)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.addWidget(self.header_table, 1)
        hrow = QVBoxLayout()  # one under the other: side by side the longer translations did not fit the panel
        for text, slot in (
            (self.tr("Add or change keyword…"), self.edit_keyword_dialog),
            (self.tr("Delete keyword"), self.delete_selected_keyword),
        ):
            b = QPushButton(text, self)
            b.setToolTip(self.tr("Only in this window until you save a copy; Ctrl+Z takes it back"))
            b.clicked.connect(slot)
            hrow.addWidget(b)
        hl.addLayout(hrow)
        self.header_note = QLabel(self)
        self.header_note.setWordWrap(True)
        hl.addWidget(self.header_note)
        self.header_save = QPushButton(self.tr("Save a copy with these header changes…"), self)
        self.header_save.setEnabled(False)
        self.header_save.setToolTip(
            self.tr(
                "The original file is not changed: a copy with the new header is written (Ctrl+Z takes back"
                " a change before that)"
            )
        )
        self.header_save.clicked.connect(
            lambda: self.header_save_requested.emit(dict(self.header_set), list(self.header_delete))
        )
        hl.addWidget(self.header_save)
        self.tabs.addTab(header_tab, self.tr("Header"))
        self.tabs.addTab(self.info, self.tr("Information"))
        self.tabs.addTab(self.graph_tab, self.tr("Graph"))
        self.float_button = QToolButton(self)
        self.float_button.setText("⧉")
        self.float_button.setCheckable(True)
        self.float_button.setToolTip(
            self.tr(
                "Results in small floating windows over the image (as MaxIm DL's Information and Graph windows); "
                "off: in these tabs"
            )
        )
        self.float_button.toggled.connect(self.set_floating)
        self.tabs.setCornerWidget(self.float_button)
        self.tabs.setMinimumWidth(150)  # a narrow page (a panel beside it) squeezes the header, not the image
        self.split = split = QSplitter(Qt.Horizontal, self)
        split.addWidget(left)
        split.addWidget(self.tabs)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 0)
        split.setSizes([900, 380])
        QVBoxLayout(self).addWidget(split)
        self.floating, self.tool_windows = False, {}
        self.set_floating(True)

    # --- open images ------------------------------------------------------------
    def open_paths(self):
        return [self.open_list.item(i).data(Qt.UserRole) for i in range(self.open_list.count())]

    def add_open(self, paths, current=None):
        """Put files in the list of open images (each once); current: the shown one, selected without reopening."""
        from PySide6.QtWidgets import QListWidgetItem

        known = self.open_paths()
        self.open_list.blockSignals(True)  # adding to an empty list must not open the first file by itself
        for p in map(str, paths):
            if p not in known:
                item = QListWidgetItem(Path(p).name)
                item.setData(Qt.UserRole, p)
                item.setToolTip(p)
                self.open_list.addItem(item)
                known.append(p)
        if current is not None and str(current) in known:
            self.open_list.setCurrentRow(known.index(str(current)))
        self.open_list.blockSignals(False)
        self.open_list.setVisible(self.open_list.count() > 1)
        self._thumbs.start(0)

    def replace_open(self, old, new):
        """A processed copy takes the place of its original in the list (the original file is not changed)."""
        paths = self.open_paths()
        if str(new) in paths or str(old) not in paths:
            return self.add_open([new])
        item = self.open_list.item(paths.index(str(old)))
        item.setText(Path(new).name)
        item.setToolTip(str(new))
        item.setData(Qt.UserRole, str(new))
        item.setData(Qt.UserRole + 1, None)
        item.setIcon(QIcon())
        self._thumbs.start(0)

    def remove_open(self, path):
        """Take a file out of the list; returns the neighbour to show next (None: the list is empty)."""
        paths = self.open_paths()
        if str(path) in paths:
            row = paths.index(str(path))
            self.open_list.blockSignals(True)
            self.open_list.takeItem(row)
            self.open_list.blockSignals(False)
            paths.pop(row)
            self.open_list.setVisible(len(paths) > 1)
            return paths[min(row, len(paths) - 1)] if paths else None
        return None

    def step_image(self, d):
        row = self.open_list.currentRow() + d
        if 0 <= row < self.open_list.count():
            self.open_list.setCurrentRow(row)

    def _list_row(self, row):
        if row >= 0:
            self.image_chosen.emit(self.open_list.item(row).data(Qt.UserRole))

    def _next_thumbnail(self):
        """Draw one missing thumbnail and come back for the next, so hundreds of files never freeze the window."""
        from PySide6.QtGui import QImage, QPixmap

        from ..io.fits import thumbnail

        for i in range(self.open_list.count()):
            item = self.open_list.item(i)
            if item.data(Qt.UserRole + 1) is None:
                item.setData(Qt.UserRole + 1, True)
                try:
                    pic = np.ascontiguousarray(thumbnail(item.data(Qt.UserRole))[::-1])  # FITS row 0 at the bottom
                    h, w = pic.shape
                    item.setIcon(QIcon(QPixmap.fromImage(QImage(pic.data, w, h, w, QImage.Format_Grayscale8).copy())))
                except Exception:  # not a FITS image (a raw camera file) or unreadable: the name alone
                    pass
                self._thumbs.start(0)
                return

    def set_floating(self, on):
        """Measurement results in small tool windows over the image (as MaxIm DL's Information and Graph windows,
        which open when a star is clicked or a line drawn), or in the tabs beside the image."""
        from PySide6.QtWidgets import QDialog

        self.floating = on
        self.float_button.setChecked(on)
        for key, widget, title, size in (
            ("info", self.info, self.tr("Information"), (420, 380)),
            ("graph", self.graph_tab, self.tr("Graph"), (460, 360)),
        ):
            win = self.tool_windows.get(key)
            if on and win is None:
                i = self.tabs.indexOf(widget)
                if i >= 0:
                    self.tabs.removeTab(i)
                win = QDialog(self, Qt.Tool)  # small, stays above the main window, closing only hides it
                win.setWindowTitle(title)
                QVBoxLayout(win).addWidget(widget)
                widget.show()
                win.resize(*size)
                self.tool_windows[key] = win
            elif not on and win is not None:
                self.tabs.addTab(widget, title)
                widget.show()
                win.hide()
                win.deleteLater()
                del self.tool_windows[key]

    def _show_tool(self, key):
        """Bring up a result: its tool window (placed at the image's right edge the first time) or its tab."""
        if not self.floating:
            if key == "info":  # in the tabs the numbers come first, as before; the graph waits in its tab
                self.tabs.setCurrentWidget(self.info)
            return
        win = self.tool_windows[key]
        if not win.isVisible():
            if not win.property("placed"):
                corner = self.viewer.mapToGlobal(self.viewer.rect().topRight())
                win.move(corner.x() - win.width() - 12, corner.y() + 12 + (0 if key == "info" else 380))
                win.setProperty("placed", True)
            win.show()
        win.raise_()

    # --- state ------------------------------------------------------------
    def undo_state(self):
        win = self.window()
        path = getattr(win, "current_path", None)
        return {
            "path": None if path is None else str(path),
            "set": {k: list(v) for k, v in self.header_set.items()},
            "delete": list(self.header_delete),
        }

    def set_undo_state(self, st):
        """The image that was shown (an operation taken back) and its header changes not yet saved."""
        win = self.window()
        current = getattr(win, "current_path", None)
        if st["path"] and str(current) != st["path"] and hasattr(win, "open_fits"):
            win.open_fits(Path(st["path"]))
        elif self.header is not None and hasattr(win, "_show_header"):
            win._show_header(self.header)  # the file's own header, then the changes of that state
        self.header_set, self.header_delete = {}, []
        for key, (value, comment) in st["set"].items():
            self.set_keyword(key, value, comment)
        for key in st["delete"]:
            self.delete_keyword(key)
        self._header_changed()

    def set_header(self, header, wcs=None):
        self.header, self.wcs = header, wcs
        self.header_set, self.header_delete = {}, []
        self._header_changed()

    def set_keyword(self, key, value, comment=""):
        """A header change waiting to be saved into a copy (shown in the table at once)."""
        from ..io.fits import STRUCTURAL

        key = key.strip().upper()
        if not key or key.rstrip("0123456789") in STRUCTURAL or (len(key) > 8 and not key.startswith("HIERARCH")):
            self.header_note.setText(self.tr("{key}: not a keyword that can be edited.").format(key=key or "—"))
            return False
        if not (str(value).isascii() and comment.isascii()):
            self.header_note.setText(self.tr("{key}: FITS headers take plain ASCII text only.").format(key=key))
            return False
        self.header_set[key] = [value, comment]
        if key in self.header_delete:
            self.header_delete.remove(key)
        rows = [i for i in range(self.header_table.rowCount()) if self.header_table.item(i, 0).text() == key]
        row = rows[0] if rows else self.header_table.rowCount()
        if not rows:
            self.header_table.insertRow(row)
        for col, text in enumerate((key, str(value), comment)):
            self.header_table.setItem(row, col, QTableWidgetItem(text))
        self._header_changed()
        return True

    def delete_keyword(self, key):
        from ..io.fits import STRUCTURAL

        if key.rstrip("0123456789") in STRUCTURAL:
            self.header_note.setText(self.tr("{key}: not a keyword that can be edited.").format(key=key))
            return False
        self.header_set.pop(key, None)
        if key not in self.header_delete:
            self.header_delete.append(key)
        for i in reversed(range(self.header_table.rowCount())):
            if self.header_table.item(i, 0).text() == key:
                self.header_table.removeRow(i)
        self._header_changed()
        return True

    def delete_selected_keyword(self):
        row = self.header_table.currentRow()
        if row >= 0:
            self.edit(self.tr("delete a keyword"), self.delete_keyword, self.header_table.item(row, 0).text())

    def edit_keyword_dialog(self):
        from ..io.fits import parse_value

        row = self.header_table.currentRow()
        start = [self.header_table.item(row, c).text() for c in range(3)] if row >= 0 else ["", "", ""]
        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("Add or change keyword"))
        form = QFormLayout(dlg)
        edits = [QLineEdit(t, dlg) for t in start]
        edits[1].setPlaceholderText(self.tr("text, number, or T / F"))
        for label, e in zip((self.tr("Keyword"), self.tr("Value"), self.tr("Comment")), edits, strict=True):
            form.addRow(label, e)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dlg)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)
        if dlg.exec() == QDialog.Accepted:
            value = parse_value(edits[1].text())
            self.edit(self.tr("change a keyword"), self.set_keyword, edits[0].text(), value, edits[2].text().strip())

    def _header_changed(self):
        n = len(self.header_set) + len(self.header_delete)
        self.header_save.setEnabled(bool(n))
        self.header_note.setText(
            self.tr("{n} change(s) not saved yet; the file itself is never changed.").format(n=n) if n else ""
        )

    def set_tool(self, key):
        self.tool_buttons[key].setChecked(True)
        self.viewer.set_tool(key)
        self.viewer.show_selection(None, 0, 0, 0, 0)

    def _gain(self):
        from ..hdr import get

        return get(self.header or {}, "EGAIN", "GAIN", default=1.0) or 1.0

    def _exptime(self):
        from ..hdr import get

        return get(self.header or {}, "EXPTIME", "EXPOSURE") or None

    def _scale(self):
        """Arcseconds per pixel from the WCS, or None."""
        if self.wcs is None:
            return None
        from astropy.wcs.utils import proj_plane_pixel_scales

        return float(np.mean(proj_plane_pixel_scales(self.wcs.celestial)) * 3600)

    def _show_rows(self, rows):
        self.info.setRowCount(len(rows))
        for i, (name, value) in enumerate(rows):
            self.info.setItem(i, 0, QTableWidgetItem(name))
            self.info.setItem(i, 1, QTableWidgetItem(value))
        self._show_tool("info")

    def _canvas(self):
        self.graph_kind.setVisible(False)  # shown again by an area measurement, the only one it applies to
        if self.graph is None:  # matplotlib only when a graph is first drawn: the page is built at start-up
            self.graph = PlotCanvas(self.graph_tab)
            self.graph_tab.layout().addWidget(self.graph, 1)
        self.graph.figure.clear()
        self._show_tool("graph")
        return self.graph

    # --- measurements -----------------------------------------------------
    def _clicked(self, x, y):
        if self.viewer.tool == "aperture":
            self.measure_star(x, y)

    def measure_star(self, x, y):
        from ..io.inspect import saturation_level, star_info

        data = self.viewer.data
        if data is None:
            return None
        r = self.radius.value() or None
        try:
            s = star_info(
                data,
                x,
                y,
                r_ap=r,
                gain=self._gain(),
                exptime=self._exptime(),
                saturation=saturation_level(self.header, data),
            )
        except Exception as e:  # no star there, at the edge, …
            self._show_rows([(self.tr("Error"), translate(e))])
            return None
        self.viewer.set_markers(
            [
                (s["x"], s["y"], s["r_ap"], "lime", ""),
                *((s["x"], s["y"], rr, "lime", "", "dash") for rr in (s["r_in"], s["r_out"])),
            ]
        )
        scale = self._scale()
        arcsec = (lambda px: f" ({px * scale:.2f}″)") if scale else (lambda px: "")
        rows = [(self.tr("Centroid x, y (FITS pixels)"), f"{s['x'] + 1:.2f}, {s['y'] + 1:.2f}")]
        if self.wcs is not None:
            ra, dec = self.wcs.celestial.pixel_to_world_values(s["x"], s["y"])
            from astropy.coordinates import SkyCoord

            c = SkyCoord(float(ra), float(dec), unit="deg")
            rows.append((self.tr("RA, Dec"), c.to_string("hmsdms", sep=":", precision=2)))
        rows += [
            (
                self.tr("Peak pixel (counts)"),
                f"{s['peak']:.1f}" + (" ⚠ " + self.tr("saturated") if s["saturated"] else ""),
            ),
            (self.tr("Background per pixel (counts)"), f"{s['background']:.2f}"),
            (self.tr("Net counts in the aperture"), f"{s['net_counts']:.1f} ± {s['net_counts_err']:.1f}"),
        ]
        if "net_electrons" in s and self._gain() != 1.0:
            rows.append((self.tr("Net electrons"), f"{s['net_electrons']:.0f}"))
        rows.append((self.tr("Signal-to-noise"), f"{s['snr']:.1f}"))
        if "instrumental_mag" in s:
            unit = self.tr("per second") if self._exptime() else self.tr("per frame")
            rows.append(
                (
                    self.tr("Instrumental magnitude ({unit})").format(unit=unit),
                    f"{s['instrumental_mag']:.3f} ± {s['instrumental_mag_err']:.3f}",
                )
            )
        rows += [
            (self.tr("FWHM (px)"), f"{s['fwhm']:.2f}" + arcsec(s["fwhm"])),
            (self.tr("Half-flux diameter (px)"), f"{s['hfd']:.2f}" + arcsec(s["hfd"])),
            (self.tr("Ellipticity, position angle (°)"), f"{s['ellipticity']:.3f}, {s['position_angle']:.0f}"),
            (self.tr("Aperture; sky annulus (px)"), f"{s['r_ap']:.2f}; {s['r_in']:.2f}–{s['r_out']:.2f}"),
            (self.tr("Pixels in the aperture"), str(s["pixels"])),
        ]
        self._show_rows(rows)
        prof = s["profile"]
        centres, binned = prof["bins"]
        g = self._canvas()
        ax = g.figure.subplots()
        ax.plot(prof["r"], prof["v"], ",", alpha=0.4)
        ax.plot(centres, binned, ".-", lw=0.8)
        ax.axvspan(0, s["r_ap"], color="#46a758", alpha=0.18, lw=0)
        ax.axvspan(s["r_in"], s["r_out"], color="#3e63dd", alpha=0.18, lw=0)
        ax.set_xlabel(self.tr("Radius (px)"))
        ax.set_ylabel(self.tr("Counts above background"))
        g.draw()
        self._graph_data = ((self.tr("Radius (px)"), self.tr("Counts above background")), centres, binned)
        return s

    def measure_area(self, x0, y0, x1, y1):
        from ..io.inspect import area_stats

        data = self.viewer.data
        if data is None:
            return None
        try:
            a = area_stats(data, x0, y0, x1, y1, gain=self._gain())
        except ValueError as e:
            self._show_rows([(self.tr("Error"), translate(e))])
            return None
        rows = [
            (self.tr("Corners x, y (FITS pixels)"), f"{a['x0'] + 1}, {a['y0'] + 1} – {a['x1'] + 1}, {a['y1'] + 1}"),
            (self.tr("Size (px)"), f"{a['width']} × {a['height']}"),
            (self.tr("Pixels"), str(a["pixels"])),
            (self.tr("Sum (counts)"), f"{a['sum']:.6g}"),
        ]
        if self._gain() != 1.0:
            rows.append((self.tr("Sum (electrons)"), f"{a['sum_electrons']:.6g}"))
        rows += [
            (self.tr("Mean"), f"{a['mean']:.3f}"),
            (self.tr("Median"), f"{a['median']:.3f}"),
            (self.tr("Standard deviation"), f"{a['std']:.3f}"),
            (self.tr("Robust standard deviation (MAD)"), f"{a['mad_std']:.3f}"),
            (self.tr("Minimum (at x, y)"), f"{a['min']:.3f} ({a['min_xy'][0] + 1}, {a['min_xy'][1] + 1})"),
            (self.tr("Maximum (at x, y)"), f"{a['max']:.3f} ({a['max_xy'][0] + 1}, {a['max_xy'][1] + 1})"),
        ]
        self._show_rows(rows)
        self._area, self._area_box = (x0, y0, x1, y1), a
        self._redraw_area()
        return a

    def measure_whole(self):
        if self.viewer.data is None:
            return None
        ny, nx = self.viewer.data.shape
        self.viewer.show_selection(None, 0, 0, 0, 0)
        return self.measure_area(0, 0, nx - 1, ny - 1)

    def _redraw_area(self):
        from ..io.inspect import box_profile, histogram

        if self._area is None or self.viewer.data is None:
            return
        data = self.viewer.data
        kind = self.graph_kind.currentData()
        g = self._canvas()
        self.graph_kind.setVisible(True)
        a = self._area_box
        if kind == "histogram":
            box = data[a["y0"] : a["y1"] + 1, a["x0"] : a["x1"] + 1]
            h = histogram(box, bins=200, clip=(0.1, 99.9))
            ax = g.figure.subplots()
            ax.stairs(h["counts"], h["edges"], fill=True, alpha=0.6)
            ax.set_yscale("log")
            labels = (self.tr("Counts"), self.tr("Number of pixels"))
            cols = ((np.array(h["edges"][:-1]) + np.array(h["edges"][1:])) / 2, h["counts"])
        elif kind == "surface":
            box = np.asarray(data[a["y0"] : a["y1"] + 1, a["x0"] : a["x1"] + 1], float)
            step = max(1, int(np.ceil(max(box.shape) / 150)))  # at most ~150 x 150 facets: drawing stays quick
            sub = box[::step, ::step]
            yy, xx = np.mgrid[: sub.shape[0], : sub.shape[1]]
            ax = g.figure.add_subplot(projection="3d")
            ax.plot_surface(a["x0"] + 1 + xx * step, a["y0"] + 1 + yy * step, sub, cmap="viridis", linewidth=0)
            ax.set_xlabel("x")
            ax.set_ylabel("y")
            labels = (self.tr("x (FITS pixels)"), self.tr("y (FITS pixels)"), self.tr("Counts"))
            cols = (a["x0"] + 1 + xx * step, a["y0"] + 1 + yy * step, sub)
        else:
            prof = box_profile(data, *self._area, axis="x" if kind == "row" else "y")
            ax = g.figure.subplots()
            cols = (np.array(prof["position"]) + 1, prof["values"])
            ax.plot(*cols, "-", lw=0.9)
            labels = (
                self.tr("x (FITS pixels)") if kind == "row" else self.tr("y (FITS pixels)"),
                self.tr("Mean counts"),
            )
        if kind != "surface":
            ax.set_xlabel(labels[0])
            ax.set_ylabel(labels[1])
        g.draw()
        self._graph_data = (labels, *cols)

    def measure_line(self, x0, y0, x1, y1):
        from ..io.inspect import line_profile

        data = self.viewer.data
        if data is None:
            return None
        p = line_profile(data, x0, y0, x1, y1, width=int(self.line_width.value()))
        vals = np.asarray(p["values"])
        scale = self._scale()
        rows = [
            (self.tr("Start x, y (FITS pixels)"), f"{x0 + 1:.1f}, {y0 + 1:.1f}"),
            (self.tr("End x, y (FITS pixels)"), f"{x1 + 1:.1f}, {y1 + 1:.1f}"),
            (self.tr("Length (px)"), f"{p['length']:.2f}" + (f" ({p['length'] * scale:.2f}″)" if scale else "")),
            (self.tr("Angle from +x (°)"), f"{p['angle']:.1f}"),
        ]
        if self.wcs is not None:
            from astropy.coordinates import SkyCoord

            (ra0, ra1), (de0, de1) = self.wcs.celestial.pixel_to_world_values([x0, x1], [y0, y1])
            a, b = SkyCoord(ra0, de0, unit="deg"), SkyCoord(ra1, de1, unit="deg")
            rows += [
                (self.tr("Separation on the sky (″)"), f"{a.separation(b).arcsec:.2f}"),
                (self.tr("Position angle on the sky (°, N through E)"), f"{a.position_angle(b).deg:.1f}"),
            ]
        rows += [
            (self.tr("Minimum, maximum along the line"), f"{vals.min():.3f}, {vals.max():.3f}"),
            (self.tr("Mean along the line"), f"{vals.mean():.3f}"),
        ]
        self._show_rows(rows)
        g = self._canvas()
        ax = g.figure.subplots()
        ax.plot(p["distance"], vals, "-", lw=0.9)
        labels = (self.tr("Distance along the line (px)"), self.tr("Counts"))
        ax.set_xlabel(labels[0])
        ax.set_ylabel(labels[1])
        g.draw()
        self._graph_data = (labels, p["distance"], vals)
        return p

    def export_graph(self, path=None):
        """The numbers behind the current graph as CSV."""
        if not self._graph_data:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, self.tr("Export data"), "graph.csv", "CSV (*.csv)")
        if not path:
            return None
        import csv

        labels, *cols = self._graph_data  # a surface has three columns: x, y, counts
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(labels)
            w.writerows(zip(*(np.ravel(c).tolist() for c in cols), strict=True))
        return path


class ProjectPage(QWidget):
    """Files in the project and the record of every step run (for reproducibility)."""

    run_selected = Signal(int)  # run id
    rerun_requested = Signal(int)  # run id

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        self.name_label = QLabel(self)
        lay.addWidget(self.name_label)
        lay.addWidget(QLabel(self.tr("Files"), self))
        self.files_list = QListWidget(self)
        lay.addWidget(self.files_list, 1)
        lay.addWidget(QLabel(self.tr("History"), self))
        self.runs_table = QTableWidget(0, 4, self)
        self.runs_table.setHorizontalHeaderLabels(
            [self.tr("Step"), self.tr("Status"), self.tr("Started"), self.tr("Settings")]
        )
        self.runs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.runs_table.horizontalHeader().setStretchLastSection(True)
        self.runs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.runs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.runs_table.itemSelectionChanged.connect(self._selected)
        lay.addWidget(self.runs_table, 1)
        row = QHBoxLayout()
        self.rerun_button = QPushButton(self.tr("Run again with the same inputs and settings"), self)
        self.rerun_button.setEnabled(False)
        self.rerun_button.setToolTip(
            self.tr("Runs the selected step again exactly as before, e.g. after the input files changed")
        )
        self.rerun_button.clicked.connect(lambda: self.rerun_requested.emit(self.selected_run()))
        row.addWidget(self.rerun_button)
        row.addStretch(1)
        lay.addLayout(row)
        self.details = QPlainTextEdit(self)
        self.details.setReadOnly(True)
        self.details.setPlaceholderText(self.tr("Select a run to see its inputs, settings, results and versions."))
        lay.addWidget(self.details, 1)

    def selected_run(self):
        item = self.runs_table.item(self.runs_table.currentRow(), 0)
        return item.data(Qt.UserRole) if item else None

    def _selected(self):
        run_id = self.selected_run()
        self.rerun_button.setEnabled(run_id is not None)
        if run_id is not None:
            self.run_selected.emit(run_id)

    def show_run(self, run):
        """Everything recorded about a run, as text (long results are cut)."""
        import json

        parts = [f"{run['step']} — {run['status']} — {run['started']}"]
        for key, title in (
            ("inputs", self.tr("Inputs")),
            ("params", self.tr("Settings")),
            ("outputs", self.tr("Results")),
            ("error", self.tr("Error")),
            ("environment", self.tr("Versions")),
        ):
            if run.get(key):
                text = run[key] if isinstance(run[key], str) else json.dumps(run[key], indent=1, default=str)
                parts.append(f"{title}:\n{text[:20000]}")
        self.details.setPlainText("\n\n".join(parts))


def by_filter(paths):
    """{filter name: paths} in the order met (FILTER keyword; "" when there is none)."""
    from astropy.io import fits

    groups = {}
    for p in paths:
        groups.setdefault(str(fits.getheader(p).get("FILTER", "") or "").strip(), []).append(p)
    return groups


class CalibratePage(QWidget):
    """Raw folder -> frame list and plan -> masters + calibrated lights."""

    scan_requested = Signal(str, str)  # calibration (or mixed) folders, light folder
    run_requested = Signal(list, str, dict)  # frames, output folder, params
    stack_requested = Signal(list, str, dict)  # calibrated images, output file, params
    photometry_requested = Signal(list)  # calibrated lights to measure

    def __init__(self, parent=None):
        super().__init__(parent)
        self.frames, self._problems, self._raw_converted, self.calibrated = [], [], 0, []
        left, right = QWidget(self), QWidget(self)  # 1. the frames | 2.–4. what is done with them
        lay = QVBoxLayout(left)
        lay.addWidget(_title(self.tr("Calibrate"), self))
        lay.addWidget(QLabel(self.tr("1. Choose your frames: the lights and the calibration frames (BDF)."), self))
        hint = QLabel(
            self.tr(
                "As they are usually kept: the lights (data) in one folder, bias / dark / flat in another. Every "
                "frame in the light folder is a light, whatever its name (nsvs…fits); in the BDF folder each frame "
                "is sorted into bias, dark or flat. Everything in one folder? Give it as the BDF folder only: the "
                "frames are then sorted by header and name. Sub-folders are read too."
            ),
            self,
        )
        hint.setWordWrap(True)
        hint.setProperty("muted", True)
        lay.addWidget(hint)
        row = QHBoxLayout()
        self.lights = QLineEdit(self)
        self.lights.setPlaceholderText(self.tr("light frames (data) folder"))
        self.lights.setToolTip(
            self.tr("Every frame here is a light, unless its header says bias, dark or flat. Sub-folders are read too.")
        )
        browse_l = QPushButton(self.tr("Browse…"), self)
        browse_l.clicked.connect(lambda: self._pick(self.lights))
        browse_l.setToolTip(self.tr("Choose the folder in a dialog"))
        row.addWidget(QLabel(self.tr("Lights"), self))
        row.addWidget(self.lights, 1)
        row.addWidget(browse_l)
        lay.addLayout(row)
        row = QHBoxLayout()
        self.folder = QLineEdit(self)
        self.folder.setPlaceholderText(self.tr("bias / dark / flat folder; another folder; …"))
        self.folder.setToolTip(
            self.tr(
                "Calibration frames, sorted into bias, dark and flat. Several folders separated by ';' (e.g. a "
                "calibration library). Everything in one folder: give it here only."
            )
        )
        browse = QPushButton(self.tr("Browse…"), self)
        browse.clicked.connect(lambda: self._pick(self.folder))
        browse.setToolTip(self.tr("Choose the folder in a dialog"))
        add_folder = QPushButton(self.tr("Add folder…"), self)
        add_folder.setToolTip(
            self.tr("Read frames from one more folder, e.g. master or calibration frames kept elsewhere")
        )
        add_folder.clicked.connect(self._add_folder)
        row.addWidget(QLabel(self.tr("BDF"), self))
        row.addWidget(self.folder, 1)
        row.addWidget(browse)
        row.addWidget(add_folder)
        lay.addLayout(row)
        self.scan_button = QPushButton(self.tr("Scan"), self)
        self.scan_button.clicked.connect(lambda: self.scan_requested.emit(self.folder.text(), self.lights.text()))
        self.scan_button.setToolTip(
            self.tr(
                "Reads every frame and sorts it by its header into bias, dark, flat, arc and light; nothing"
                " is changed yet, check the table"
            )
        )
        self.clock_offset = QDoubleSpinBox(self)
        self.clock_offset.setRange(-14, 14)
        self.clock_offset.setDecimals(2)
        self.clock_offset.setPrefix(self.tr("DSLR clock − UTC: "))
        self.clock_offset.setSuffix(self.tr(" h"))
        self.clock_offset.setToolTip(
            self.tr(
                "Camera raw files (CR2, NEF, ARW, DNG…) are converted to FITS in the folder fits_from_raw. Their "
                "time is the camera clock: give how many hours it is ahead of UTC (0 if the camera is set to UTC), "
                "and check the clock against a time signal — timing errors go straight into minima and O−C."
            )
        )
        row = QHBoxLayout()  # a second row: the first stays narrow enough for two columns on a small screen
        for w in (self.clock_offset, self.scan_button):
            row.addWidget(w)
        row.addStretch(1)
        lay.addLayout(row)
        self.summary = QLabel(self)
        lay.addWidget(self.summary)
        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(
            [
                self.tr("File"),
                self.tr("Type"),
                self.tr("Exposure (s)"),
                self.tr("Filter"),
                self.tr("Temp. (°C)"),
                self.tr("Binning"),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self._edit_kind)
        self.table.setToolTip(self.tr("Double-click a frame's type to change it"))
        lay.addWidget(self.table, 1)
        how = QLabel(
            self.tr(
                "How the type is found: the header (IMAGETYP, FRAME, OBSTYPE…) first; without it a word in the file "
                "name — bias / zero / offset, dark, flat / twilight, arc / lamp; a frame of 0 s is a bias. Every "
                "other frame is a light (e.g. named after the star: nsvs…fits); only a type the header states "
                "and the program does not know (FOCUS, TEST…) is “unknown” and left out. Double-click a type to "
                "change it."
            ),
            self,
        )
        how.setWordWrap(True)
        how.setProperty("muted", True)
        lay.addWidget(how)
        self.warnings = QPlainTextEdit(self)
        self.warnings.setReadOnly(True)
        self.warnings.setMaximumHeight(90)
        self.warnings.setPlaceholderText(self.tr("Problems and missing calibration frames are listed here."))
        lay.addWidget(self.warnings)
        lay = QVBoxLayout(right)
        lay.addWidget(QLabel(self.tr("2. Choose where to write master frames and calibrated images."), self))
        row = QHBoxLayout()
        self.output = QLineEdit(self)
        browse_out = QPushButton(self.tr("Browse…"), self)
        browse_out.clicked.connect(lambda: self._pick(self.output))
        self.output.setToolTip(
            self.tr(
                "Folder for the master frames and the calibrated images; created if it does not exist. The "
                "raw frames are never changed."
            )
        )
        browse_out.setToolTip(self.tr("Choose the folder in a dialog"))
        row.addWidget(self.output)
        row.addWidget(browse_out)
        lay.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Rejection (sigma):"), self))
        self.sigma = QDoubleSpinBox(self)
        self.sigma.setRange(1.5, 10.0)
        self.sigma.setSingleStep(0.5)
        self.sigma.setValue(3.0)
        self.sigma.setToolTip(
            self.tr(
                "A pixel further than this many standard deviations from the other frames' values is left "
                "out when the masters are combined and when images are stacked; 3 is the usual value"
            )
        )
        row.addWidget(self.sigma)
        self.cosmics = QCheckBox(self.tr("Remove cosmic rays from lights"), self)
        self.cosmics.setToolTip(
            self.tr(
                "Finds cosmic-ray hits in each light by their sharp edges (L.A.Cosmic, astroscrappy) and "
                "replaces them. Useful for long exposures and spectra; when many frames are stacked with "
                "rejection it is not needed."
            )
        )
        row.addWidget(self.cosmics)
        self.optimize_dark = QCheckBox(self.tr("Scale the dark to each light (dark optimisation)"), self)
        self.optimize_dark.setToolTip(
            self.tr("Finds the dark scale that leaves the least noise; useful when the camera temperature drifted")
        )
        self.fix_defects = QCheckBox(self.tr("Repair hot and dead pixels (defect map from the masters)"), self)
        self.fix_defects.setToolTip(
            self.tr(
                "Hot pixels (from the master dark) and dead pixels (from the master flat) are replaced by "
                "the median of their neighbours in every light; the map is saved with the masters"
            )
        )
        self.spectra = QCheckBox(self.tr("Spectra: do not divide by the flat"), self)
        self.spectra.setToolTip(
            self.tr(
                "For echelle and long-slit frames: the flat between the orders is near zero, so dividing by it "
                "would blow up the noise. The master flat is still made; give it to the Spectroscopy page."
            )
        )
        self.split_colour = QCheckBox(self.tr("Colour camera: each colour as its own image"), self)
        self.split_colour.setChecked(True)
        self.split_colour.setToolTip(
            self.tr(
                "Frames with a Bayer pattern (BAYERPAT) are calibrated as a mosaic, then written as three half-size "
                "images R, G, B (filters TR, TG, TB) without interpolation; G is closest to V. "
                "Monochrome frames are not affected."
            )
        )
        row.addStretch(1)
        self.run_button = QPushButton(self.tr("3. Calibrate"), self)
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self._run)
        self.run_button.setToolTip(
            self.tr(
                "Makes the master bias, dark and flat and writes every light as (light − bias − dark) / "
                "flat into the output folder"
            )
        )
        row.addWidget(self.run_button)
        lay.addLayout(row)
        self.linearity = QLineEdit(self)
        self.linearity.setPlaceholderText(self.tr("linearity correction c0 c1 c2 … (empty: none)"))
        self.linearity.setToolTip(
            self.tr(
                "The camera's non-linearity: every raw value v becomes c0 + c1·v + c2·v² + … before calibration "
                "(from the maker's sheet or a series of flats of rising exposure)"
            )
        )
        self.more_options = Collapsible(self.tr("More calibration options"), self)
        for w in (self.optimize_dark, self.fix_defects, self.split_colour, self.spectra, self.linearity):
            self.more_options.body.addWidget(w)
        lay.addWidget(self.more_options)
        self.result = QLabel(self)
        self.result.setWordWrap(True)
        lay.addWidget(self.result)
        self.photometry_button = QPushButton(self.tr("4. Measure them on the Photometry page →"), self)
        self.photometry_button.setEnabled(False)
        self.photometry_button.setToolTip(
            self.tr("Sends the calibrated lights to the Photometry page and opens it (a light curve, a variable star)")
        )
        self.photometry_button.clicked.connect(lambda: self.photometry_requested.emit(list(self.calibrated)))
        lay.addWidget(self.photometry_button)
        self.stack_button = QPushButton(self.tr("Or: stack them into one deep picture (not for a light curve)"), self)
        self.stack_button.setEnabled(False)
        self.stack_button.clicked.connect(self._stack)
        self.stack_button.setToolTip(
            self.tr(
                "Aligns the calibrated images on their stars and adds them into one image per filter: fainter stars "
                "and nebulae show, for a picture, astrometry or a colour image. Not needed for photometry: a light "
                "curve measures every single image (a stack has one time only)."
            )
        )
        lay.addWidget(self.stack_button)
        opts = QGridLayout()
        self.stack_opts = {}
        choices = {
            "method": (
                self.tr("Combine"),
                {"mean": self.tr("mean"), "median": self.tr("median"), "sum": self.tr("sum")},
            ),
            "rejection": (
                self.tr("Reject"),
                {
                    "sigma": self.tr("sigma clipping"),
                    "winsorized": self.tr("winsorized sigma clipping"),
                    "minmax": self.tr("min / max (drop lowest and highest)"),
                    "percentile": self.tr("percentile clipping"),
                    "none": self.tr("none"),
                },
            ),
            "normalize": (
                self.tr("Normalise"),
                {
                    "none": self.tr("none"),
                    "multiplicative": self.tr("multiplicative (scale to the first frame)"),
                    "additive": self.tr("additive (shift to the first frame)"),
                },
            ),
            "weighting": (self.tr("Weights"), {"none": self.tr("equal"), "noise": self.tr("by noise (1 / σ²)")}),
            "align": (
                self.tr("Align"),
                {
                    "translation": self.tr("shift only"),
                    "stars": self.tr("star patterns (rotation and scale too)"),
                },
            ),
        }
        tips = {
            "method": self.tr("mean: the least noise; median: robust without rejection; sum: keeps the counts"),
            "rejection": self.tr(
                "Pixels unlike the others (satellites, cosmic rays, hot pixels) are left out before combining; "
                "sigma clipping needs about ten frames or more, min / max works with fewer"
            ),
            "normalize": self.tr(
                "Brings the frames to the same level before rejection: multiplicative when the transparency "
                "changed, additive when the sky background changed"
            ),
            "weighting": self.tr("By noise: noisier frames (thin cloud, twilight) count less"),
            "align": self.tr(
                "Shift only: an equatorial mount without field rotation; star patterns: the field rotates or the "
                "scale differs (alt-az mount, meridian flip, another telescope)"
            ),
        }
        for i, (key, (label, items)) in enumerate(choices.items()):
            box = QComboBox(self)
            for value, text in items.items():
                box.addItem(text, value)
            self.stack_opts[key] = box
            box.setToolTip(tips[key])
            opts.addWidget(QLabel(label, self), i // 2, 2 * (i % 2))
            opts.addWidget(box, i // 2, 2 * (i % 2) + 1)
        self.clip_low, self.clip_high = QDoubleSpinBox(self), QDoubleSpinBox(self)
        for w, v in ((self.clip_low, 1), (self.clip_high, 1)):
            w.setRange(0, 50)
            w.setDecimals(2)
            w.setValue(v)
            w.setToolTip(self.tr("min / max: how many values to drop; percentile: the fraction of the median"))
        opts.addWidget(QLabel(self.tr("Low / high"), self), 2, 2)
        lh = QHBoxLayout()
        lh.addWidget(self.clip_low)
        lh.addWidget(self.clip_high)
        opts.addLayout(lh, 2, 3)
        self.stack_options = Collapsible(self.tr("Stacking options"), self)
        self.stack_options.body.addLayout(opts)
        self.drizzle = QCheckBox(self.tr("Drizzle onto a 2× finer grid (undersampled, dithered frames)"), self)
        self.drizzle.setToolTip(
            self.tr(
                "For stars only one or two pixels wide (FWHM under about 2 px) in frames shifted a little "
                "between exposures: recovers detail on a grid twice as fine (Fruchter & Hook 2002). Needs "
                "many frames; otherwise leave it off."
            )
        )
        self.stack_options.body.addWidget(self.drizzle)
        lay.addWidget(self.stack_options)
        lay.addStretch(1)
        split = QSplitter(Qt.Horizontal, self)  # two columns: on a short window nothing is below the fold
        split.addWidget(left)
        split.addWidget(right)
        split.setChildrenCollapsible(False)
        split.setSizes([3000, 2000])
        QVBoxLayout(self).addWidget(split)
        self.calibrated = []

    def stack_params(self):
        params = {k: box.currentData() for k, box in self.stack_opts.items()} | {"sigma": self.sigma.value()}
        low, high = self.clip_low.value(), self.clip_high.value()
        if params["rejection"] == "minmax":
            low, high = int(low), int(high)
        elif params["rejection"] == "percentile" and (low >= 1 or high >= 1):  # given in percent
            low, high = low / 100, high / 100
        return params | {"low": low, "high": high}

    def _stack(self):
        """One stack per filter (a colour camera's R, G, B channels are filters TR, TG, TB): frames taken through
        different filters must never be combined."""
        name = "drizzle" if self.drizzle.isChecked() else "stack"
        groups = by_filter(self.calibrated)
        single = [filt or "—" for filt, paths in groups.items() if len(paths) < 2]
        self.result.setText(
            self.tr("Stacking…")
            + (
                " " + self.tr("Only one frame through {f}: nothing to stack.").format(f=", ".join(single))
                if single
                else ""
            )
        )
        for filt, paths in groups.items():
            if len(paths) < 2:
                continue
            suffix = f"_{re.sub(r'[^A-Za-z0-9.+-]+', '_', filt).strip('_')}" if len(groups) > 1 else ""
            params = {"drizzle": True} if self.drizzle.isChecked() else self.stack_params()
            self.stack_requested.emit(paths, str(Path(self.output.text()) / f"{name}{suffix}.fits"), params)

    def _pick(self, line_edit):
        folder = QFileDialog.getExistingDirectory(self, self.tr("Choose folder"), self._first(line_edit.text()))
        if folder:
            line_edit.setText(folder)
            if line_edit is self.folder and not self.output.text():
                self.output.setText(str(Path(folder) / "calibrated"))

    @staticmethod
    def _first(text):
        return next((f.strip() for f in text.split(";") if f.strip()), "")

    def _add_folder(self, folder=None):
        """One more folder to read frames from (several folders are separated by ";")."""
        folder = folder or QFileDialog.getExistingDirectory(
            self, self.tr("Add folder"), self._first(self.folder.text())
        )
        if folder:
            current = [f.strip() for f in self.folder.text().split(";") if f.strip()]
            self.folder.setText("; ".join(current + [folder]))
            if not self.output.text():
                self.output.setText(str(Path(self._first(self.folder.text())) / "calibrated"))

    def _edit_kind(self, row, col):
        """Double-click on a type: a list of the types; the choice is used for the calibration (the files are not
        changed)."""
        if col != 1 or row >= len(self.frames):
            return
        names = self._kind_names()
        box = QComboBox(self.table)
        for key, text in names.items():
            box.addItem(text, key)
        box.setCurrentIndex(max(0, box.findData(self.frames[row]["kind"])))

        def chosen(i):
            self.frames[row] = dict(self.frames[row]) | {"kind": box.itemData(i)}
            self.show_frames(self.frames, self._problems, self._raw_converted)

        box.activated.connect(chosen)
        self.table.setCellWidget(row, 1, box)
        box.showPopup()

    def _kind_names(self):
        return {
            "bias": self.tr("bias"),
            "dark": self.tr("dark"),
            "flat": self.tr("flat"),
            "light": self.tr("light"),
            "arc": self.tr("arc lamp"),
            "unknown": self.tr("unknown"),
        }

    def show_frames(self, frames: list[dict], problems: list, raw_converted: int = 0):
        self.frames, self._problems, self._raw_converted = frames, problems, raw_converted
        self.table.clearContents()
        base = self.lights.text().strip() or self._first(self.folder.text())
        if not self.output.text() and base:
            self.output.setText(str(Path(base) / "calibrated"))
        kinds = self._kind_names()
        self.table.setRowCount(len(frames))
        for r, f in enumerate(frames):
            values = (
                Path(f["path"]).name,
                kinds[f["kind"]],
                f["exptime"],
                f["filter"],
                None if f["temperature"] is None else f"{f['temperature']:.1f}",
                "×".join(map(str, f["binning"])),
            )
            for c, v in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem("" if v is None else str(v)))
        counts = {k: sum(f["kind"] == k for f in frames) for k in kinds}
        text = "  ".join(f"{kinds[k]}: {n}" for k, n in counts.items() if n)
        if raw_converted:
            text += "  " + self.tr("({n} camera raw files read; times: camera clock − {h} h)").format(
                n=raw_converted, h=f"{self.clock_offset.value():g}"
            )
        self.summary.setText(text)
        plan = make_plan([Frame(**f | {"binning": tuple(f["binning"]), "shape": tuple(f["shape"])}) for f in frames])
        cannot = self.tr("Cannot read {file}: {error}")
        lines = [cannot.format(file=Path(p).name, error=translate(e)) for p, e in problems]
        lines += [self.tr("Type unknown, ignored: {file}").format(file=Path(p).name) for p in plan.unknown]
        lines += [f"{Path(p).name}: {self._missing_text(k, why)}" for p, k, why in plan.missing]
        if frames and not counts["light"]:
            lines.insert(
                0,
                self.tr(
                    "No light frames found, so there is nothing to calibrate yet. If the lights are in another "
                    "folder, choose the folder that holds both (sub-folders are read) or add it with “Add folder…”."
                ),
            )
        self.warnings.setPlainText("\n".join(lines))
        self.run_button.setEnabled(counts["light"] + counts["arc"] > 0)
        self.run_button.setToolTip("" if counts["light"] else self.tr("Needs at least one light frame"))

    def _missing_text(self, kind, w):
        size = f"{w['shape'][1]}×{w['shape'][0]}, bin {w['binning'][0]}×{w['binning'][1]}"
        if kind == "flat":
            return self.tr("no flat for filter '{filter}' ({size}); will be calibrated without flat").format(
                filter=w["filter"] or "—", size=size
            )
        if kind == "dark":
            return self.tr(
                "no dark for {t} s within {tol} °C of {temp} °C (darks of another exposure need bias "
                "frames to be scaled); will be calibrated without dark"
            ).format(t=w["exptime"], tol=w["temp_tol"], temp=w["temperature"])
        return self.tr("no bias ({size}); will be calibrated without bias").format(size=size)

    def _run(self):
        self.result.setText(self.tr("Calibrating…"))
        params = {"sigma": self.sigma.value(), "cosmic_rays": self.cosmics.isChecked()}
        params |= {"optimize_dark": self.optimize_dark.isChecked(), "fix_defects": self.fix_defects.isChecked()}
        params["divide_flat"] = not self.spectra.isChecked()
        params["split_colour"] = self.split_colour.isChecked()
        try:
            params["linearity"] = [float(v) for v in self.linearity.text().replace(",", " ").split()]
        except ValueError:
            self.result.setText(self.tr("Linearity correction: write numbers c0 c1 c2 …, e.g. 0 1 4e-6"))
            return
        self.run_requested.emit(self.frames, self.output.text(), params)

    def show_result(self, out: dict):
        self.calibrated = out["calibrated"]
        self.stack_button.setEnabled(len(self.calibrated) > 1)
        self.photometry_button.setEnabled(bool(self.calibrated))
        self.result.setText(
            self.tr("Done: {n} images calibrated, {m} master frames written to {folder}.").format(
                n=len(out["calibrated"]), m=len(out["masters"]), folder=self.output.text()
            )
            + (
                " " + self.tr("{n} arc lamp frames calibrated (bias and dark only).").format(n=len(out["arcs"]))
                if out.get("arcs")
                else ""
            )
            + (
                " "
                + self.tr("Dark scaled by {lo:.3f}–{hi:.3f} (DARKSCAL in each file's header).").format(
                    lo=min(out["dark_scales"]), hi=max(out["dark_scales"])
                )
                if out.get("dark_scales")
                else ""
            )
        )
        from .messages import translate

        unused = out.get("unused_groups") or []
        if unused:  # not combined: no light needs them (another size, binning, filter or setting)
            self.result.setText(
                self.result.text()
                + " "
                + self.tr("{n} groups of calibration frames fit no light and were not combined (e.g. {file}).").format(
                    n=len(unused), file=unused[0]["file"]
                )
            )
        failed = out.get("failed_masters") or []
        if failed:  # said where the user looks for problems, the frames list's note box
            kinds = {"bias": self.tr("bias"), "dark": self.tr("dark"), "flat": self.tr("flat")}
            lines = [
                self.tr("Master {kind} not made from {n} frames (e.g. {file}), calibrated without it: {why}").format(
                    kind=kinds.get(f["kind"], f["kind"]), n=f["frames"], file=f["file"], why=translate(f["reason"])
                )
                for f in failed
            ]
            self.warnings.setPlainText("\n".join(lines + [self.warnings.toPlainText()]).strip())


class PlotCanvas(QWidget):
    """A matplotlib figure in the window (the same library makes the publication-quality exports)."""

    def __init__(self, parent=None, figure=None):
        super().__init__(parent)
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
        from matplotlib.figure import Figure

        self.figure = figure or Figure(figsize=(6, 3), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        toolbar = NavigationToolbar2QT(self.canvas, self)
        toolbar.addAction(self.tr("Publication figure…"), self.export_publication)
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


class PhotometryPage(Undoable, QWidget):
    """Pick target and comparison stars on the first image, measure, plot, time the minimum."""

    measure_requested = Signal(list, list, list, str, dict)  # images, target_xy, comps_xy, coord, params
    suggest_requested = Signal(list, list, dict)  # images, target_xy, params
    minimum_requested = Signal(dict, dict)  # light curve, params
    live_updated = Signal()
    polarimetry_requested = Signal(list, list, list, dict)  # images, o_xy, e_xy, params
    quality_requested = Signal(list)  # images
    catalog_requested = Signal(dict, dict)  # inputs, params
    apertures_requested = Signal(list, list, list)  # images, target_xy, comps_xy
    next_requested = Signal(str, str)  # the page to go on to ("timeseries" / "orbits"), the light curve file or ""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_undo()
        self.images, self.target, self.comps, self.light_curve = [], None, [], None
        self.ref, self.shown, self.skipped = None, 0, set()  # the frame the stars are marked on, the one shown, unused
        self.extras, self.lc_raw, self.detrend_cfg = [], None, None  # extras: [((x, y), "target" | "check")]
        self.excluded, self._frame_ids, self._plotted = set(), [], None  # frames deleted by hand
        self.live, self.live_folder, self.live_seen, self._live_busy = None, None, set(), False
        # the image above the light curve on the left, the controls the whole height on the right: a light-curve
        # band across the page squeezed the controls into a strip whose buttons were only found by scrolling
        split = QSplitter(Qt.Vertical, self)
        self._split = split
        self.viewer = ImageViewer(self)
        self.viewer.clicked.connect(self._clicked)
        self.viewer.rings_wheel.connect(self._rings_wheel)
        split.addWidget(self.viewer)
        from PySide6.QtWidgets import QScrollArea

        side_box = QWidget(self)
        side = QVBoxLayout(side_box)
        side.addWidget(_title(self.tr("Photometry"), self))
        self.load_button = QPushButton(self.tr("Choose images…"), self)
        self.load_button.clicked.connect(self._choose_images)
        self.load_button.setToolTip(
            self.tr(
                "The calibrated frames of one field (FITS, also TESS / Kepler target pixel files); they are"
                " sorted by time"
            )
        )
        side.addWidget(self.load_button)
        self.images_label = QLabel(self.tr("No images"), self)
        self.images_label.setWordWrap(True)
        side.addWidget(self.images_label)
        # every frame can be looked at, marked on, or left out (the owner: "I only see one picture")
        browse = QHBoxLayout()
        self.prev_frame, self.next_frame = QToolButton(self), QToolButton(self)
        self.prev_frame.setArrowType(Qt.LeftArrow)
        self.next_frame.setArrowType(Qt.RightArrow)
        self.prev_frame.setToolTip(self.tr("Previous frame (in time)"))
        self.next_frame.setToolTip(self.tr("Next frame (in time)"))
        self.frame_slider = QSlider(Qt.Horizontal, self)
        self.frame_slider.setToolTip(self.tr("Go through the frames of the series"))
        self.prev_frame.clicked.connect(lambda: self.frame_slider.setValue(self.frame_slider.value() - 1))
        self.next_frame.clicked.connect(lambda: self.frame_slider.setValue(self.frame_slider.value() + 1))
        self.frame_slider.valueChanged.connect(self.show_frame)
        for w in (self.prev_frame, self.frame_slider, self.next_frame):
            browse.addWidget(w, 1 if w is self.frame_slider else 0)
        side.addLayout(browse)
        self.frame_label = QLabel(self)
        self.frame_label.setWordWrap(True)
        side.addWidget(self.frame_label)
        self.use_frame = QCheckBox(self.tr("Use this frame"), self)
        self.use_frame.setToolTip(
            self.tr("Untick to leave this frame out of the light curve (clouds, a satellite trail, a bad focus)")
        )
        self.use_frame.toggled.connect(self._use_frame)
        side.addWidget(self.use_frame)
        # every frame in a list, as MaxIm DL shows them: click one to see it, untick to leave it out
        self.frame_table = QTableWidget(0, 4, self)
        self.frame_table.setHorizontalHeaderLabels([self.tr("Frame"), self.tr("Time (UTC)"), "FWHM", self.tr("Sky")])
        self.frame_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.frame_table.horizontalHeader().setStretchLastSection(True)
        self.frame_table.verticalHeader().setDefaultSectionSize(20)
        self.frame_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.frame_table.setSelectionMode(QTableWidget.SingleSelection)
        self.frame_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.frame_table.setMinimumHeight(110)
        self.frame_table.setMaximumHeight(200)
        self.frame_table.setToolTip(
            self.tr(
                "Every frame of the series: click one to show it, untick it to leave it out. FWHM and sky are filled "
                "by “Find the bad frames”; bad frames are red."
            )
        )
        self.frame_table.currentCellChanged.connect(
            lambda row, *_: self.frame_slider.setValue(row) if row >= 0 else None
        )
        self.frame_table.itemChanged.connect(self._frame_checked)
        side.addWidget(self.frame_table)
        self.blink = QPushButton(self.tr("Blink"), self)
        self.blink.setCheckable(True)
        self.blink.setToolTip(
            self.tr(
                "Shows the frames used one after the other (about 2 a second): a passing cloud, a satellite trail, a "
                "jump in the pointing or a missing star catches the eye at once. Click again to stop."
            )
        )
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(450)
        self._blink_timer.timeout.connect(self._blink_step)
        self.blink.toggled.connect(lambda on: self._blink_timer.start() if on else self._blink_timer.stop())
        side.addWidget(self.blink)
        for w in (self.prev_frame, self.frame_slider, self.next_frame, self.use_frame, self.blink):
            w.setEnabled(False)
        self.quality_button = QPushButton(self.tr("Find the bad frames (clouds, focus, trails)"), self)
        self.quality_button.setToolTip(
            self.tr(
                "Optional, before measuring: measures every frame's star size (FWHM), sky brightness and number of "
                "stars, and names the frames far from the night's usual values (passing clouds, lost focus or "
                "tracking, twilight). You then choose to leave them out; nothing is removed by itself."
            )
        )
        self.quality_button.setEnabled(False)
        self.quality_button.clicked.connect(lambda: self.quality_requested.emit(self._series()))
        side.addWidget(self.quality_button)
        self.drop_bad = QPushButton(self.tr("Leave out the bad frames"), self)
        self.drop_bad.hide()
        self.drop_bad.clicked.connect(self._drop_bad)
        self.drop_bad.setToolTip(
            self.tr("Takes the frames the quality check marked as bad out of the list; the files stay on disk")
        )
        side.addWidget(self.drop_bad)
        hint = QLabel(
            self.tr("Click the target star, then one or more comparison stars. A click on a marked star takes it off."),
            self,
        )
        hint.setWordWrap(True)
        side.addWidget(hint)
        role_row = QHBoxLayout()
        role_row.addWidget(QLabel(self.tr("Clicks add:"), self))
        self.click_role = QComboBox(self)
        self.click_role.addItem(self.tr("target, then comparison stars"), "auto")
        self.click_role.addItem(self.tr("check stars"), "check")
        self.click_role.addItem(self.tr("more targets"), "target")
        self.click_role.currentIndexChanged.connect(lambda *_: self._draw_markers())
        self.click_role.setToolTip(
            self.tr("Check stars and further targets are measured against the same comparison stars, not used in them")
        )
        role_row.addWidget(self.click_role, 1)
        side.addLayout(role_row)
        clear = QPushButton(self.tr("Clear stars"), self)
        clear.clicked.connect(lambda: self.edit(self.tr("clear the stars"), self._clear))
        clear.setToolTip(self.tr("Takes off every marked star (Ctrl+Z brings them back)"))
        side.addWidget(clear)
        self.suggest_button = QPushButton(self.tr("Suggest comparison stars"), self)
        self.suggest_button.setEnabled(False)
        self.suggest_button.setToolTip(
            self.tr("Similar brightness, not saturated, no bright neighbour, inside the frame in every image")
        )
        self.suggest_button.clicked.connect(
            lambda: self.suggest_requested.emit(self._series(), list(self.target), {"r_out": self.r_out.value()})
        )
        side.addWidget(self.suggest_button)
        grid = QGridLayout()
        self.r_ap, self.r_in, self.r_out = (self._spin(v) for v in (4.0, 10.0, 16.0))
        self.r_out.setToolTip(
            self.tr("Outer edge of the sky ring; the ring should hold several times as many pixels as the aperture")
        )
        self.r_in.setToolTip(
            self.tr(
                "The sky is measured in a ring around the star starting at this radius, where the star's "
                "light has ended (at least 3 FWHM)"
            )
        )
        self.r_ap.setToolTip(
            self.tr(
                "Radius of the circle in which the star's light is added up; about 1 to 2 times the FWHM "
                "gives the best signal-to-noise"
            )
        )
        for row, (label, w) in enumerate(
            (
                (self.tr("Ring 1 — the star's light inside (px)"), self.r_ap),
                (self.tr("Ring 2 — the sky starts (px)"), self.r_in),
                (self.tr("Ring 3 — the sky ends (px)"), self.r_out),
            )
        ):
            grid.addWidget(QLabel(label, self), row, 0)
            grid.addWidget(w, row, 1)
        side.addLayout(grid)
        rings_note = QLabel(
            self.tr(
                "Radii in image pixels: the rings grow with the zoom. Between rings 1 and 2 nothing is measured "
                "(the star's faint wings); between 2 and 3 the sky. Shift + mouse wheel on the image makes them "
                "larger or smaller."
            ),
            self,
        )
        rings_note.setWordWrap(True)
        side.addWidget(rings_note)
        self.apertures_button = QPushButton(self.tr("Choose the radii from the star profiles"), self)
        self.apertures_button.setToolTip(
            self.tr(
                "Measures the stars' FWHM; aperture = best signal-to-noise (1–3 FWHM), sky from where the star's "
                "light has ended (at least 3 FWHM) with four times as many pixels as the aperture"
            )
        )
        self.apertures_button.setEnabled(False)
        self.apertures_button.clicked.connect(
            lambda: self.apertures_requested.emit(self._series(), list(self.target), [list(c) for c in self.comps])
        )
        side.addWidget(self.apertures_button)
        self.follow_seeing = QCheckBox(self.tr("Radii follow the seeing (scaled by each frame's FWHM)"), self)
        self.follow_seeing.setToolTip(
            self.tr(
                "Each frame's radii are scaled by its FWHM over the first frame's, so the aperture holds "
                "the same part of the light when the seeing changes during the night. In a crowded field a changing "
                "aperture can add trends of its own: measure once with fixed radii too and compare"
            )
        )
        self.measure_options = Collapsible(self.tr("More measuring options: seeing, PSF, scintillation"), self)
        self.measure_options.body.addWidget(self.follow_seeing)
        self.psf = QCheckBox(self.tr("PSF photometry (crowded fields: blended stars fitted together)"), self)
        self.psf.setToolTip(
            self.tr(
                "For crowded fields: stars that overlap are fitted together with the image's star profile "
                "instead of being added up in a circle. Slower; for isolated stars the aperture is as good."
            )
        )
        self.measure_options.body.addWidget(self.psf)
        side.addWidget(QLabel(self.tr("Target RA Dec (for BJD), e.g. 02:04:10.3 +46:41:16"), self))
        self.coord = QLineEdit(self)
        self.coord.setToolTip(
            self.tr(
                "Needed to turn the times into BJD (barycentric). Empty: taken from the header (OBJCTRA / "
                "OBJCTDEC or RA / DEC)."
            )
        )
        side.addWidget(self.coord)
        tel = QHBoxLayout()
        tel.addWidget(QLabel(self.tr("Telescope aperture (m)"), self))
        self.telescope_d = QDoubleSpinBox(self)
        self.telescope_d.setRange(0.0, 50.0)
        self.telescope_d.setDecimals(3)
        self.telescope_d.setSingleStep(0.05)
        self.telescope_d.setSpecialValueText(self.tr("from the header"))
        self.telescope_d.setToolTip(
            self.tr(
                "For the scintillation noise in the error bars (Osborn et al. 2015). 0: APTDIA from the header; "
                "without it, scintillation is not included"
            )
        )
        tel.addWidget(self.telescope_d)
        self.measure_options.body.addLayout(tel)
        side.addWidget(self.measure_options)
        self.measure_button = QPushButton(self.tr("Measure light curve"), self)
        self.measure_button.setEnabled(False)
        self.measure_button.clicked.connect(self._measure)
        self.measure_button.setToolTip(
            self.tr(
                "Measures the marked stars in every image and draws the differential light curve (target "
                "against the comparison stars)"
            )
        )
        side.addWidget(self.measure_button)
        self.live_button = QPushButton(self.tr("Live: follow a folder during the night…"), self)
        self.live_button.setCheckable(True)
        self.live_button.setToolTip(
            self.tr(
                "Each new frame in the folder is calibrated (optional masters) and measured as it arrives; "
                "the light curve grows on its own."
            )
        )
        self.live_button.toggled.connect(self._toggle_live)
        # rarely used tools: out of the main steps, one click away (PLAN 4.8 item 16)
        self.other_tools = Collapsible(self.tr("Other tools: live light curve, polarimetry"), self)
        self.other_tools.body.addWidget(self.live_button)
        self.pol_button = QPushButton(self.tr("Polarimetry (dual beam)"), self)
        self.pol_button.setToolTip(
            self.tr(
                "Click the ordinary image of the star as target and its extraordinary image as the first "
                "comparison; the half-wave-plate angle is read from the header."
            )
        )
        self.pol_button.clicked.connect(self._polarimetry)
        self.other_tools.body.addWidget(self.pol_button)
        side.addWidget(self.other_tools)
        side.addStretch(1)
        scroll = QScrollArea(self)  # small screens: the panel scrolls instead of pushing the window taller
        scroll.setWidget(side_box)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(side_box.sizeHint().width() + 20)

        bottom = QWidget(self)
        b_lay = QHBoxLayout(bottom)
        self.plot = PlotCanvas(bottom)
        b_lay.addWidget(self.plot, 3)
        res = QVBoxLayout()
        self.res_tabs = QTabWidget(self)
        # stars: roles, typed-in comparison magnitudes, weights
        stars_tab = QWidget(self)
        sl = QVBoxLayout(stars_tab)
        self.star_table = QTableWidget(0, 5, self)
        self.star_table.setHorizontalHeaderLabels(
            [self.tr("Star"), self.tr("Role"), "x", "y", self.tr("Known magnitude")]
        )
        self.star_table.horizontalHeader().setStretchLastSection(True)
        for col in range(4):
            self.star_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.star_table.verticalHeader().hide()
        self.star_table.setToolTip(
            self.tr("Type the comparison stars' magnitudes (from a chart or catalogue) to get the target's magnitude")
        )
        self.star_table.itemChanged.connect(lambda *_: self._recompute())
        sl.addWidget(self.star_table, 1)
        self.weighted = QCheckBox(self.tr("Weight comparison stars by their scatter"), self)
        self.weighted.setToolTip(
            self.tr("Each comparison star is measured against the others; noisy or variable ones count less")
        )
        self.weighted.toggled.connect(lambda *_: self._recompute())
        sl.addWidget(self.weighted)
        self.res_tabs.addTab(stars_tab, self.tr("Stars"))
        # plot and detrending
        plot_tab = QWidget(self)
        pl = QVBoxLayout(plot_tab)
        self.show_what = QComboBox(self)
        self.show_what.setPlaceholderText(self.tr("Measure a light curve to choose what to plot"))
        self.show_what.setEnabled(False)
        self.show_what.currentIndexChanged.connect(lambda *_: self._plot_current())
        self.show_what.setToolTip(
            self.tr(
                "Which curve to draw: the target against the comparison stars, the checks, the comparison "
                "stars against each other, sky, FWHM, airmass…"
            )
        )
        pl.addWidget(self.show_what)
        edit_row = QHBoxLayout()
        self.delete_mode = QCheckBox(self.tr("Click a point to delete it"), self)
        self.delete_mode.setToolTip(
            self.tr("For a bad frame (cloud, satellite, wrong star): it is left out of every result, export included")
        )
        edit_row.addWidget(self.delete_mode)
        restore = QPushButton(self.tr("Restore deleted points"), self)
        restore.clicked.connect(self.restore_points)
        restore.setToolTip(self.tr("Brings back every point deleted by clicking"))
        edit_row.addWidget(restore)
        pl.addLayout(edit_row)
        space_row = QHBoxLayout()
        space_row.addWidget(QLabel(self.tr("Spacing between curves"), self))
        self.spacing = QDoubleSpinBox(self)
        self.spacing.setRange(0.0, 2.0)
        self.spacing.setSingleStep(0.01)
        self.spacing.setDecimals(3)
        self.spacing.setValue(0.05)
        self.spacing.setToolTip(self.tr("For the views with several curves; 0 puts them on top of each other"))
        self.spacing.valueChanged.connect(lambda *_: self._plot_current())
        space_row.addWidget(self.spacing)
        pl.addLayout(space_row)
        pl.addWidget(QLabel(self.tr("Detrend against:"), self))
        trend_row = QGridLayout()
        self.trend_boxes = {}
        names = {
            "airmass": self.tr("airmass"),
            "fwhm": self.tr("FWHM"),
            "sky": self.tr("sky"),
            "x": "x",
            "y": "y",
            "time": self.tr("time"),
        }
        trend_tips = {
            "airmass": self.tr("Extinction: the stars change with their height above the horizon"),
            "fwhm": self.tr("Seeing: larger star images lose more light outside the aperture"),
            "sky": self.tr("Sky brightness: twilight, moonlight, thin cloud"),
            "x": self.tr("Position on the chip: the stars drift over pixels of different sensitivity"),
            "y": self.tr("Position on the chip: the stars drift over pixels of different sensitivity"),
            "time": self.tr("A slow change with time"),
        }
        for i, (key, text) in enumerate(names.items()):
            box = QCheckBox(text, self)
            box.setToolTip(trend_tips[key])
            self.trend_boxes[key] = box
            trend_row.addWidget(box, i // 3, i % 3)
        pl.addLayout(trend_row)
        from PySide6.QtWidgets import QSpinBox

        deg_row = QHBoxLayout()
        self.trend_degree = QSpinBox(self)
        self.trend_degree.setRange(1, 3)
        self.trend_degree.setToolTip(self.tr("1: linear; 2 or 3: curved trends (a polynomial in each quantity)"))
        deg_row.addWidget(QLabel(self.tr("Trend degree"), self))
        deg_row.addWidget(self.trend_degree)
        deg_row.addStretch(1)
        pl.addLayout(deg_row)
        ex_row = QHBoxLayout()
        ex_row.addWidget(QLabel(self.tr("Leave out from"), self))
        self.exclude_from = QLineEdit(self)
        self.exclude_to = QLineEdit(self)
        for w in (self.exclude_from, self.exclude_to):
            w.setPlaceholderText(self.tr("time"))
            w.setToolTip(
                self.tr(
                    "Points in this time range (the eclipse or transit itself) are left out of the trend fit, "
                    "then corrected with it"
                )
            )
        ex_row.addWidget(self.exclude_from)
        ex_row.addWidget(QLabel(self.tr("to"), self))
        ex_row.addWidget(self.exclude_to)
        pl.addLayout(ex_row)
        d_row = QHBoxLayout()
        self.detrend_button = QPushButton(self.tr("Detrend"), self)
        self.detrend_button.setToolTip(
            self.tr("Fits ln(flux) linearly in the ticked quantities on the points outside the left-out range")
        )
        self.detrend_button.clicked.connect(self._detrend)
        self.undo_detrend = QPushButton(self.tr("Undo detrending"), self)
        self.undo_detrend.clicked.connect(lambda: self._set_detrend(None))
        self.undo_detrend.setToolTip(self.tr("Back to the light curve before detrending"))
        d_row.addWidget(self.detrend_button)
        d_row.addWidget(self.undo_detrend)
        pl.addLayout(d_row)
        pl.addStretch(1)
        self.res_tabs.addTab(plot_tab, self.tr("Plot"))
        # minimum
        min_tab = QWidget(self)
        ml = QVBoxLayout(min_tab)
        grid = QGridLayout()
        self.t0 = QLineEdit(self)
        self.t0.setPlaceholderText(self.tr("optional"))
        self.period = QLineEdit(self)
        self.period.setPlaceholderText(self.tr("optional"))
        grid.addWidget(QLabel(self.tr("Ephemeris T0 (BJD)"), self), 0, 0)
        grid.addWidget(self.t0, 0, 1)
        grid.addWidget(QLabel(self.tr("Period (d)"), self), 1, 0)
        grid.addWidget(self.period, 1, 1)
        ml.addLayout(grid)
        self.period.setToolTip(self.tr("Optional: with T0 and the period the minimum gets its cycle number and O−C"))
        self.t0.setToolTip(self.tr("Optional: with T0 and the period the minimum gets its cycle number and O−C"))
        from PySide6.QtWidgets import QButtonGroup, QGroupBox

        method_box = QGroupBox(self.tr("What kind of minimum is it?"), self)
        mb = QVBoxLayout(method_box)
        self.kvw = QRadioButton(self.tr("Eclipsing binary: Kwee–van Woerden method"), self)
        self.kvw.setToolTip(
            self.tr(
                "Kwee & van Woerden (1956), the standard method for minima of eclipsing binaries and the times "
                "collected in O−C databases: the time about which the descending and ascending branches are most "
                "symmetric, with its error"
            )
        )
        self.trapezoid = QRadioButton(self.tr("Exoplanet transit: trapezoid fit"), self)
        self.trapezoid.setToolTip(
            self.tr(
                "A trapezoid (ingress, flat bottom, egress) fitted to the dip: mid-transit time with its error, "
                "depth and duration, as the ExoClock and ETD projects use"
            )
        )
        self.kvw.setChecked(True)
        group = QButtonGroup(method_box)
        for b in (self.kvw, self.trapezoid):
            group.addButton(b)
            mb.addWidget(b)
        note = QLabel(
            self.tr(
                "Choose by what you observe: a V-shaped or rounded minimum of a binary star, or the flat-bottomed "
                "dip of a planet passing in front of its star."
            ),
            self,
        )
        note.setWordWrap(True)
        note.setProperty("muted", True)
        mb.addWidget(note)
        ml.addWidget(method_box)
        self.minimum_button = QPushButton(self.tr("Time of minimum"), self)
        self.minimum_button.setEnabled(False)
        self.minimum_button.clicked.connect(self._minimum)
        self.minimum_button.setToolTip(
            self.tr(
                "Time of minimum of the curve shown, with its error (every minimum if the night holds more than one)"
            )
        )
        ml.addWidget(self.minimum_button)
        ml.addStretch(1)
        self.res_tabs.addTab(min_tab, self.tr("Minimum"))
        # export and standard magnitudes
        out_tab = QWidget(self)
        ol = QVBoxLayout(out_tab)
        self.export_button = QPushButton(self.tr("Export CSV…"), self)
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export)
        self.export_button.setToolTip(
            self.tr("Time, flux, magnitude and error of every star as a table for a spreadsheet or another program")
        )
        ol.addWidget(self.export_button)
        row = QHBoxLayout()
        self.band = QComboBox(self)
        self.band.addItems(("V", "B", "R", "I", "G", "SG", "SR", "SI", "CV"))
        self.band.setToolTip(self.tr("Filter of the images (CV: unfiltered, reduced to V)"))
        self.catalog_button = QPushButton(self.tr("Standard magnitudes (APASS / Gaia)"), self)
        self.catalog_button.setToolTip(
            self.tr(
                "Looks up the comparison stars in APASS and Gaia (needs the internet and a plate-solved first "
                "image) and turns the light curve into magnitudes in the standard system"
            )
        )
        self.catalog_button.setEnabled(False)
        self.catalog_button.clicked.connect(self._catalog)
        row.addWidget(self.band)
        row.addWidget(self.catalog_button, 1)
        ol.addLayout(row)
        self.catalog = None
        self.aavso_button = QPushButton(self.tr("Export AAVSO report…"), self)
        self.aavso_button.setEnabled(False)
        self.aavso_button.clicked.connect(self._export_aavso)
        self.aavso_button.setToolTip(
            self.tr(
                "A report in AAVSO's Extended File Format to submit through WebObs; the comparison stars' "
                "magnitudes are asked for"
            )
        )
        ol.addWidget(self.aavso_button)
        ol.addStretch(1)
        self.res_tabs.addTab(out_tab, self.tr("Export"))
        res.addWidget(self.res_tabs, 1)
        self.result = QLabel(self)
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        res.addWidget(self.result)
        # photometry only measures; the fits are on the next pages — say so where the result appears
        self.next_box = QWidget(self)
        nb = QVBoxLayout(self.next_box)
        nb.setContentsMargins(0, 0, 0, 0)
        note = QLabel(
            self.tr(
                "Photometry measures the brightness; the fits come next: the period and the times of minimum "
                "(O−C) on Light curves & O−C, a physical model of an eclipsing binary or a transit on Orbits & "
                "models (formulas: Guide, Mathematics of the methods)."
            ),
            self,
        )
        note.setWordWrap(True)
        nb.addWidget(note)
        go_period = QPushButton(self.tr("Period search and O−C →"), self)
        go_period.setToolTip(self.tr("Opens Light curves & O−C, which already has this light curve"))
        go_period.clicked.connect(lambda: self.next_requested.emit("timeseries", ""))
        go_model = QPushButton(self.tr("Fit an eclipse or transit model →"), self)
        go_model.setToolTip(self.tr("Saves the light curve as a CSV file and opens it on Orbits & models"))
        go_model.clicked.connect(self._to_models)
        nb.addWidget(go_period)
        nb.addWidget(go_model)
        self.next_box.setVisible(False)
        res.addWidget(self.next_box)
        widest = max(self.res_tabs.widget(i).minimumSizeHint().width() for i in range(self.res_tabs.count()))
        self.res_tabs.setMinimumWidth(widest + 30)  # scrolling only up and down: never cut a control's text
        for i in range(self.res_tabs.count()):  # a tab's controls scroll rather than take the image's height
            text, inner = self.res_tabs.tabText(i), self.res_tabs.widget(i)
            box = QScrollArea(self)
            box.setWidgetResizable(True)
            box.setFrameShape(QScrollArea.NoFrame)
            box.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.res_tabs.removeTab(i)
            box.setWidget(inner)
            self.res_tabs.insertTab(i, box, text)
        self.res_tabs.setCurrentIndex(0)
        b_lay.addLayout(res, 1)
        split.addWidget(bottom)
        self._lower = bottom  # the light curve and the star table: shown once a star is marked
        bottom.setVisible(False)
        page = QSplitter(Qt.Horizontal, self)
        page.addWidget(split)
        page.addWidget(scroll)
        page.setStretchFactor(0, 1)
        page.setStretchFactor(1, 0)
        page.setChildrenCollapsible(False)
        QVBoxLayout(self).addWidget(page)

    def _polarimetry(self):
        if not (self.images and self.target and self.comps):
            self.result.setText(self.tr("Click the ordinary and the extraordinary image of the star first."))
            return
        params = {"r_ap": self.r_ap.value(), "r_in": self.r_in.value(), "r_out": self.r_out.value()}
        self.result.setText(self.tr("Measuring…"))
        self.polarimetry_requested.emit(self._series(), list(self.target), list(self.comps[0]), params)

    def show_polarimetry(self, r):
        self.result.setText(
            self.tr(
                "q = {q:.5f} ± {qe:.5f}, u = {u:.5f} ± {ue:.5f}, P = {p:.3f} ± {pe:.3f} % "
                "(debiased {p0:.3f} %), θ = {t:.1f} ± {te:.1f}°; {n} frames, angles: {src}"
            ).format(
                q=r["q"],
                qe=r["q_err"],
                u=r["u"],
                ue=r["u_err"],
                p=100 * r["p"],
                pe=100 * r["p_err"],
                p0=100 * r["p_debiased"],
                t=r["theta"],
                te=r["theta_err"],
                n=r["n"],
                src=r["angle_source"],
            )
        )

    # --- live -------------------------------------------------------------
    def _toggle_live(self, on):
        if not on:
            self.stop_live()
            return
        folder = QFileDialog.getExistingDirectory(self, self.tr("Folder the camera writes to"))
        if not folder:
            self.live_button.setChecked(False)
            return
        masters, _ = QFileDialog.getOpenFileNames(
            self, self.tr("Master bias / dark / flat (optional; Cancel for none)"), folder, "FITS (*.fits *.fit *.fts)"
        )
        self.start_live(folder, masters)

    def start_live(self, folder, masters=()):
        """Follow folder. Without stars yet, the first frame is shown to click them; press Live again."""
        from ..photometry import live

        if not (self.target and self.comps):
            first = live.ready_files(folder, set(), min_age_s=0)
            if first:
                self.set_images(first[:1])
            self.result.setText(self.tr("Click the target and comparison stars on the first frame, then start Live."))
            self.live_button.setChecked(False)
            return False
        self.live = live.LiveLightCurve(
            self.target,
            self.comps,
            self.r_ap.value(),
            self.r_in.value(),
            self.r_out.value(),
            self.coord.text().strip() or None,
            masters=live.load_masters(masters),
        )
        self.live_folder, self.live_seen = folder, set()
        self.live_updated.connect(self._live_show)
        self._live_timer = QTimer(self)
        self._live_timer.timeout.connect(self.poll_live)
        self._live_timer.start(3000)
        self.result.setText(self.tr("Live: waiting for frames in {f}").format(f=folder))
        self.poll_live()
        return True

    def stop_live(self):
        if getattr(self, "_live_timer", None):
            self._live_timer.stop()
            self._live_timer = None
            try:
                self.live_updated.disconnect(self._live_show)
            except RuntimeError:
                pass

    def poll_live(self):
        """Measure the frames that arrived since the last poll, in a background thread."""
        import threading

        from ..photometry import live

        if self.live is None or self._live_busy:
            return
        new = live.ready_files(self.live_folder, self.live_seen)
        if not new:
            return
        self._live_busy = True

        def work(session=self.live):
            try:
                for p in new:
                    self.live_seen.add(p)
                    session.add(p)
            finally:
                self._live_busy = False
                try:
                    self.live_updated.emit()
                except RuntimeError:  # page closed meanwhile
                    pass

        threading.Thread(target=work, daemon=True).start()

    def _live_show(self):
        if self.live and self.live.points:
            self.show_light_curve(self.live.light_curve())
            if self.live.failed:
                self.result.setText(
                    self.result.text() + " " + self.tr("{n} frames skipped.").format(n=len(self.live.failed))
                )

    def _spin(self, value):
        w = QDoubleSpinBox(self)
        w.setRange(0.5, 200)
        w.setSingleStep(0.5)
        w.setValue(value)
        w.valueChanged.connect(self._draw_markers)
        return w

    def _choose_images(self):
        from .files import images_filter

        paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Choose images"), "", images_filter())
        if paths:
            self.set_images(paths)

    def set_images(self, paths):
        from .. import timing
        from ..io.bayer import fits_paths
        from ..io.fits import read_image

        paths = fits_paths(paths)  # camera raw files and pictures get a FITS copy every tool can read

        self.quality_button.setEnabled(True)
        self.images = timing.chronological(paths)
        self.ref, self.shown, self.skipped = None, 0, set()
        data, header, _ = read_image(self.images[0])
        self.viewer.set_image(data)
        self.frame_slider.blockSignals(True)
        self.frame_slider.setRange(0, len(self.images) - 1)
        self.frame_slider.setValue(0)
        self.frame_slider.blockSignals(False)
        for w in (self.prev_frame, self.frame_slider, self.next_frame, self.use_frame, self.blink):
            w.setEnabled(True)
        self.quality = []
        self._fill_frames()
        self._frame_text(header)
        sky = None
        try:
            from ..photometry.lightcurve import target_coord

            sky = target_coord(header)
        except Exception:  # header position unreadable: the user types it
            pass
        if sky is not None and not self.coord.text():
            self.coord.setText(sky.to_string("hmsdms", sep=":", precision=1))
        text = self.tr("{n} images, first: {name}").format(n=len(self.images), name=Path(self.images[0]).name)
        if "TPFSKIP" in header:  # a TESS / Kepler file: say what was left out, the user may want them back
            text += "\n" + self.tr(
                "Target pixel file: {n} cadences left out (no time, or flagged as useless by the mission)."
            ).format(n=header["TPFSKIP"])
        if "DATE-CAM" in header:  # a phone or camera picture: its time is the camera clock, often local time
            text += "\n" + self.tr(
                "Times: camera clock − {h} h. A camera on local time needs DSLR clock − UTC on the Calibrate page."
            ).format(h=f"{header.get('CLKOFFS', 0):g}")
        self.images_label.setText(text)
        self._clear()
        self.undo_stack.clear()  # stars marked on other frames: their history goes with them

    def undo_state(self):
        return {
            "target": self.target,
            "ref": self.ref,
            "comps": list(self.comps),
            "extras": list(self.extras),
            "excluded": sorted(self.excluded),
            "detrend": self.detrend_cfg,
        }

    def set_undo_state(self, st):
        self.target, self.comps, self.extras = st["target"], list(st["comps"]), list(st["extras"])
        self.ref = st.get("ref")
        self._draw_markers()
        if (set(st["excluded"]), st["detrend"]) != (self.excluded, self.detrend_cfg):
            self.excluded, self.detrend_cfg = set(st["excluded"]), st["detrend"]
            if self.lc_raw is not None:
                self._recompute()

    def _clicked(self, x, y):
        self.edit(self.tr("mark or unmark a star"), self._mark, x, y)

    def _mark(self, x, y):
        if self._star_names() and self.ref not in (None, self.shown):
            self.result.setText(
                self.tr(
                    "The stars are marked on frame {k}: go back to it to change them, or Clear stars to mark them on "
                    "this frame."
                ).format(k=self.ref + 1)
            )
            return
        if not self._star_names():
            self.ref = self.shown  # positions are taken on this frame; the measurement carries them to the others
        near = [xy for _, _, xy in self._star_names() if (xy[0] - x) ** 2 + (xy[1] - y) ** 2 <= self.r_ap.value() ** 2]
        if near:  # a click on a marked star takes it off again, instead of marking it twice
            xy = near[0]
            self.target = None if self.target == xy else self.target
            self.comps = [c for c in self.comps if c != xy]
            self.extras = [e for e in self.extras if e[0] != xy]
            if self.target is None and self.comps:  # the first comparison is not promoted: say it
                self.result.setText(self.tr("The target was removed: click the new target."))
            self._draw_markers()
            return
        role = self.click_role.currentData()
        if role in ("check", "target") and self.target is not None:
            self.extras.append(((x, y), role))
        elif self.target is None:
            self.target = (x, y)
        else:
            self.comps.append((x, y))
        self._draw_markers()

    def _clear(self):
        self.target, self.comps, self.extras = None, [], []
        self.ref = None
        self._draw_markers()

    def _frame_text(self, header=None):
        from .. import timing

        path = self.images[self.shown]
        when = ""
        try:
            when = timing.mid_time(header).utc.isot[:19].replace("T", " ") + " UTC" if header is not None else ""
        except Exception:  # no time in the file: the name says enough
            pass
        text = self.tr("Frame {k} of {n}: {name}").format(k=self.shown + 1, n=len(self.images), name=Path(path).name)
        if when:
            text += f", {when}"
        if self.ref is not None:
            text += "\n" + (
                self.tr("The stars are marked on this frame.")
                if self.ref == self.shown
                else self.tr("The stars are marked on frame {k}.").format(k=self.ref + 1)
            )
        self.frame_label.setText(text)
        self.use_frame.blockSignals(True)
        self.use_frame.setChecked(path not in self.skipped)
        self.use_frame.blockSignals(False)

    def show_frame(self, i):
        """Show frame i of the series; the marked stars are drawn on the frame they were marked on."""
        from ..io.fits import read_image

        if not self.images:
            return
        self.shown = max(0, min(int(i), len(self.images) - 1))
        data, header, _ = read_image(self.images[self.shown])
        self.viewer.set_image(data, keep_view=True)  # browsing and blinking keep the zoom
        self._draw_markers()
        self._frame_text(header)
        self.frame_table.blockSignals(True)
        self.frame_table.selectRow(self.shown)
        self.frame_table.blockSignals(False)

    def _use_frame(self, on):
        item = self.frame_table.item(self.shown, 0)
        if item is not None:
            item.setCheckState(Qt.Checked if on else Qt.Unchecked)  # the list does the rest (_frame_checked)
            return
        path = self.images[self.shown]
        if on:
            self.skipped.discard(path)
        elif len(self.skipped) + 1 < len(self.images):
            self.skipped.add(path)
        self._frame_text()
        used = len(self.images) - len(self.skipped)
        self.images_label.setText(self.tr("{n} images, {k} of them used").format(n=len(self.images), k=used))

    def _fill_frames(self):
        """The frame list: name, mid-exposure time, the quality numbers when measured, the use box."""
        from astropy.io import fits

        from .. import timing
        from ..io.fits import find_image_hdu, inherited

        quality = {r["file"]: r for r in getattr(self, "quality", None) or []}
        self.frame_table.blockSignals(True)
        self.frame_table.setRowCount(len(self.images))
        for i, path in enumerate(self.images):
            when = ""
            try:
                with fits.open(path) as hdul:
                    when = timing.mid_time(inherited(hdul, find_image_hdu(hdul))).utc.isot[11:19]
            except Exception:  # no time in the file: the name is enough
                pass
            q = quality.get(path, {})
            fwhm, sky = q.get("fwhm"), q.get("background")
            cells = (Path(path).name, when, "" if fwhm is None else f"{fwhm:.2f}", "" if sky is None else f"{sky:.0f}")
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if col == 0:
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Unchecked if path in self.skipped else Qt.Checked)
                if q and not q.get("good", True):
                    from PySide6.QtGui import QColor

                    item.setForeground(QColor("#e5484d"))
                    item.setToolTip(", ".join(translate(w) for w in q.get("why", [])))
                self.frame_table.setItem(i, col, item)
        self.frame_table.selectRow(self.shown)
        self.frame_table.blockSignals(False)

    def _frame_checked(self, item):
        if item.column() != 0:
            return
        path = self.images[item.row()]
        on = item.checkState() == Qt.Checked
        if not on and len(self.skipped) + 1 >= len(self.images):  # one frame at least stays in
            self.frame_table.blockSignals(True)
            item.setCheckState(Qt.Checked)
            self.frame_table.blockSignals(False)
            return
        (self.skipped.discard if on else self.skipped.add)(path)
        self._frame_text()
        self.images_label.setText(
            self.tr("{n} images, {k} of them used").format(n=len(self.images), k=len(self.images) - len(self.skipped))
        )

    def _blink_step(self):
        """The next frame in use (round the series)."""
        used = [i for i, p in enumerate(self.images) if p not in self.skipped]
        if len(used) < 2:
            self.blink.setChecked(False)
            return
        later = [i for i in used if i > self.shown]
        self.frame_slider.setValue(later[0] if later else used[0])

    def _series(self):
        """The frames to measure, the frame with the marked stars first (where the positions belong)."""
        used = [p for p in self.images if p not in self.skipped]
        ref = self.images[self.ref or 0]
        return [ref] + [p for p in used if p != ref] if ref in used else used

    def _star_names(self):
        """[(name, role, (x, y))]: T1 target, C1… comparison, T2… further targets, K1… check stars."""
        out = [("T1", "target", self.target)] if self.target else []
        out += [(f"C{i + 1}", "comparison", c) for i, c in enumerate(self.comps)]
        n_t = n_k = 0
        for xy, role in self.extras:
            if role == "target":
                n_t += 1
                out.append((f"T{n_t + 1}", "target", xy))
            else:
                n_k += 1
                out.append((f"K{n_k}", "check", xy))
        return out

    def _fill_star_table(self):
        known = self._known_mags_by_name()
        roles = {"target": self.tr("target"), "comparison": self.tr("comparison"), "check": self.tr("check")}
        stars = self._star_names()
        self.star_table.blockSignals(True)
        self.star_table.setRowCount(len(stars))
        for i, (name, role, (x, y)) in enumerate(stars):
            for col, text in enumerate((name, roles[role], f"{x + 1:.1f}", f"{y + 1:.1f}", known.get(name, ""))):
                item = QTableWidgetItem(text)
                if col < 4:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.star_table.setItem(i, col, item)
        self.star_table.blockSignals(False)

    def _known_mags_by_name(self):
        out = {}
        for i in range(self.star_table.rowCount()):
            name, mag = self.star_table.item(i, 0), self.star_table.item(i, 4)
            if name and mag and mag.text().strip():
                out[name.text()] = mag.text().strip()
        return out

    def known_comp_mags(self):
        """Magnitudes of the comparison stars in their order: typed in the star table, else from the catalogue
        look-up (None where neither has one)."""
        known = self._known_mags_by_name()
        cat = (self.catalog or {}).get("comps") or []
        n = len(self.lc_raw["comp_flux"][0]) if self.lc_raw else len(self.comps)
        out = []
        for i in range(n):
            try:
                out.append(float(known[f"C{i + 1}"].replace(",", ".")))
            except (KeyError, ValueError):
                out.append(cat[i]["mag"] if i < len(cat) and cat[i] else None)
        return out

    def _show_lower(self, on):
        """The lower panel (light curve, star table) only when there is something in it: until then the image has
        the whole height (the owner found the empty band in the way)."""
        if on and self._lower.isHidden():
            self._lower.setVisible(True)
            total = max(sum(self._split.sizes()), 500)
            self._split.setSizes([total * 3 // 5, total * 2 // 5])
        elif not on:
            self._lower.setVisible(False)

    def _rings_wheel(self, step):
        """Shift + wheel on the image: all three rings 0.5 px larger / smaller, the gap and the sky ring keep their
        widths; ring 1 never below 1 px."""
        d = 0.5 * step
        if self.r_ap.value() + d < 1:
            return
        for w in (self.r_out, self.r_in, self.r_ap) if d > 0 else (self.r_ap, self.r_in, self.r_out):
            w.setValue(w.value() + d)

    def _draw_markers(self):
        """Three rings per star: the aperture (solid), the inner and outer edge of the sky annulus (dashed); the
        gap between the aperture and the annulus is measured by neither."""
        r, r_in, r_out = self.r_ap.value(), self.r_in.value(), self.r_out.value()
        colours = {"target": "lime", "comparison": "red", "check": "#ffb224"}
        stars = [(xy, colours[role], name) for name, role, xy in self._star_names()]
        self._show_lower(bool(stars) or self.lc_raw is not None)
        self._fill_star_table()
        marks = []
        here = self.ref is None or self.ref == self.shown
        for xy, colour, label in stars if here else ():
            marks += [(*xy, r, colour, label), (*xy, r_in, colour, "", "dash"), (*xy, r_out, colour, "", "dash")]
        self.viewer.set_markers(marks)
        role = self.click_role.currentData()
        nxt = "target" if self.target is None or role == "target" else "check" if role == "check" else "comparison"
        # the rings of the next click follow the mouse, in the colour of the star it will mark
        self.viewer.set_pick(True, [(r, False), (r_in, True), (r_out, True)], colours[nxt])
        self.apertures_button.setEnabled(bool(self.images and self.target))
        self.measure_button.setEnabled(bool(self.images and self.target))  # no comparison: the target's own flux
        self.catalog_button.setEnabled(bool(self.images and self.target and self.comps))
        self.suggest_button.setEnabled(bool(self.images and self.target))

    def set_comparisons(self, comps):
        self.edit(self.tr("suggested comparison stars"), self._set_comps, [tuple(c) for c in comps])

    def _set_comps(self, comps):
        self.comps = comps
        self._draw_markers()
        if not comps:
            self.result.setText(self.tr("No suitable comparison star found; click them by hand."))
        else:
            self.result.setText(
                self.tr(
                    "{n} comparison stars suggested: similar brightness, near the target, unsaturated, no neighbour "
                    "in the sky ring, inside every frame. Click one to take it off, or click others to add them."
                ).format(n=len(comps))
            )

    def _measure(self):
        params = {"r_ap": self.r_ap.value(), "r_in": self.r_in.value(), "r_out": self.r_out.value()}
        params["follow_seeing"] = self.follow_seeing.isChecked()
        if self.telescope_d.value() > 0:
            params["aperture_m"] = self.telescope_d.value()
        params["psf"] = self.psf.isChecked()
        if self.extras:
            params["extra_xy"] = [list(xy) for xy, _ in self.extras]
        self.result.setText(self.tr("Measuring…"))
        series = self._series()
        params["ref_image"] = series[0]  # the positions belong to this frame; the step carries them to the others
        self.measure_requested.emit(
            series, list(self.target), [list(c) for c in self.comps], self.coord.text().strip(), params
        )

    def show_apertures(self, a):
        """Set the three radii and draw the star's radial profile with them (like a seeing profile)."""
        for w, key in ((self.r_ap, "r_ap"), (self.r_in, "r_in"), (self.r_out, "r_out")):
            w.setValue(a[key])
        self.plot.figure.clear()
        ax = self.plot.figure.subplots()
        ax.axvspan(0, a["r_ap"], color="#46a758", alpha=0.18, lw=0, label=self.tr("aperture"))
        ax.axvspan(a["r_in"], a["r_out"], color="#3e63dd", alpha=0.18, lw=0, label=self.tr("sky annulus"))
        ax.plot(a["profile_r"], a["profile"], ".-", lw=0.8, ms=4, label=self.tr("star profile (peak = 1)"))
        ax.axhline(0, color="grey", lw=0.5)
        ax.axhline(0.5, color="grey", lw=0.5, ls=":")
        for r in (a["r_ap"], a["r_in"], a["r_out"]):
            ax.axvline(r, color="grey", lw=0.8, ls="--")
        ax.set_xlim(0, a["r_out"] * 1.15)
        ax.set_xlabel(self.tr("Radius (px)"))
        ax.set_ylabel(self.tr("Relative brightness"))
        ax.legend(fontsize=8)
        self.plot.draw()
        self.result.setText(
            self.tr(
                "FWHM {f:.2f} px. Aperture {a:.2f} px ({af:.1f} FWHM; best S/N at {b:.2f} px; holds {ee:.1f} % of the "
                "light). Gap {a:.2f}–{i:.2f} px is left out. Sky annulus {i:.2f}–{o:.2f} px."
            ).format(
                f=a["fwhm"],
                a=a["r_ap"],
                af=a["r_ap"] / a["fwhm"],
                b=a["best_snr_radius"],
                ee=100 * a["encircled_at_aperture"],
                i=a["r_in"],
                o=a["r_out"],
            )
            + (
                "\n"
                + self.tr(
                    "The target's light grows {x:.1f} % more than the comparison stars' between 1 and 1.5 apertures: "
                    "something faint is next to it. Keep the radii fixed (not following the seeing); its light then "
                    "only dilutes the depth a little."
                ).format(x=100 * a["target_excess"])
                if a.get("target_excess", 0) > 0.01
                else ""
            )
        )

    def show_quality(self, rows):
        """Plot FWHM, number of stars and sky of every frame; bad ones in red, with the reasons."""
        from .messages import translate

        self.quality = rows
        self._show_lower(True)  # the plot is in the lower panel
        self._fill_frames()
        n = np.arange(len(rows))
        bad = np.array([not r["good"] for r in rows])
        self.plot.figure.clear()
        axes = self.plot.figure.subplots(3, 1, sharex=True)
        for ax, key, label in zip(
            axes,
            ("fwhm", "stars", "background"),
            (self.tr("FWHM (px)"), self.tr("Stars"), self.tr("Sky (ADU)")),
            strict=True,
        ):
            y = np.array([np.nan if r[key] is None else r[key] for r in rows], float)
            ax.plot(n, y, ".-", lw=0.6, ms=4)
            ax.plot(n[bad], y[bad], "o", color="#e5484d", ms=6)
            ax.set_ylabel(label)
        axes[-1].set_xlabel(self.tr("Frame"))
        self.plot.draw()
        reasons = [
            f"{r['file'].replace(chr(92), '/').split('/')[-1]}: {', '.join(translate(w) for w in r['why'])}"
            for r in rows
            if not r["good"]
        ]
        self.result.setText(
            self.tr("{g} of {n} frames are good.").format(g=len(rows) - len(reasons), n=len(rows))
            + "".join("\n" + t for t in reasons[:12])
        )
        self.drop_bad.setVisible(bool(reasons))

    def _drop_bad(self):
        """The bad frames are unticked in the list (not deleted: a tick brings one back)."""
        bad = {r["file"] for r in self.quality if not r["good"]}
        self.skipped |= bad & set(self.images)
        if len(self.skipped) >= len(self.images):
            self.skipped -= bad
        self._fill_frames()
        self._frame_text()
        self.images_label.setText(
            self.tr("{n} images, {k} of them used").format(n=len(self.images), k=len(self.images) - len(self.skipped))
        )
        self.drop_bad.hide()

    def _catalog(self):
        inputs = {"image": self._series()[0], "target_xy": list(self.target), "comps_xy": [list(c) for c in self.comps]}
        self.result.setText(self.tr("Looking up the comparison stars…"))
        self.catalog_requested.emit(inputs, {"filter": self.band.currentText()})

    def show_catalog(self, cat):
        """Comparison magnitudes found: written into the star table's known-magnitude column, so the target's
        standard magnitudes (with the colour term) come from the same calculation as typed-in magnitudes."""
        self.catalog = cat
        lines = [
            self.tr("Comparison {i}: {m:.3f} ± {e:.3f} ({src})").format(
                i=i + 1, m=c["mag"], e=c["err"], src=c["source"]
            )
            if c
            else self.tr("Comparison {i}: not in the catalogues").format(i=i + 1)
            for i, c in enumerate(cat["comps"])
        ]
        self.star_table.blockSignals(True)
        for i, c in enumerate(cat["comps"]):
            row = 1 + i  # T1 is the first row, then C1, C2…
            if c and row < self.star_table.rowCount():
                self.star_table.setItem(row, 4, QTableWidgetItem(f"{c['mag']:.6f}"))
        self.star_table.blockSignals(False)
        if self.lc_raw is None and self.light_curve is not None:
            self.lc_raw = self.light_curve
        if self.lc_raw is not None:
            if not self.show_what.count():
                self._fill_show_choices()
            self._recompute()
            lc = self.light_curve
            if "mag" in lc:
                m = np.asarray(lc["mag"])
                lines.append(
                    self.tr("Target {band}: {lo:.3f} – {hi:.3f} mag").format(
                        band=lc["mag_band"], lo=np.nanmin(m), hi=np.nanmax(m)
                    )
                )
                self.show_what.setCurrentIndex(self.show_what.findData("mag"))
        self.result.setText("\n".join(lines))

    def show_light_curve(self, lc):
        """A new measurement: kept as measured; weights, detrending and magnitudes are applied on top of it."""
        self.lc_raw, self.detrend_cfg, self.excluded = lc, None, set()
        self._show_lower(True)
        self.next_box.setVisible(True)
        self.minimum_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.aavso_button.setEnabled(True)
        self._fill_show_choices()
        self._recompute()

    def _fill_show_choices(self):
        current = self.show_what.currentData()
        self.show_what.blockSignals(True)
        self.show_what.setEnabled(True)
        self.show_what.clear()
        self.show_what.addItem(self.tr("Differential: target − comparison, the check star above it"), "diff")
        self.show_what.addItem(self.tr("T1: relative flux"), "rel")
        self.show_what.addItem(self.tr("T1: differential magnitude (Δm)"), "dmag")
        self.show_what.addItem(self.tr("T1: magnitude (needs known magnitudes)"), "mag")
        for i, (name, _role, _) in enumerate(n for n in self._star_names() if n[1] != "comparison" and n[0] != "T1"):
            self.show_what.addItem(self.tr("{name}: relative flux").format(name=name), f"extra{i}")
        self.show_what.addItem(self.tr("Comparison stars against the others"), "comps")
        self.show_what.addItem(self.tr("All stars, normalised and offset"), "all")
        self.show_what.addItem(self.tr("Airmass, sky, FWHM and position"), "trends")
        i = self.show_what.findData(current)
        self.show_what.setCurrentIndex(max(i, 0))
        self.show_what.blockSignals(False)

    def _recompute(self):
        """Current light curve = measured one, with the chosen ensemble weights, detrending and magnitudes."""
        from ..photometry import differential as d
        from ..photometry.catalog import calibrate

        raw = self.lc_raw
        if raw is None:
            return
        raw, self._frame_ids = _without_frames(raw, self.excluded)
        lc = dict(raw)
        w = None
        if "comp_flux_err" in raw:  # light curves of older projects and the live one keep their own ensemble
            if self.weighted.isChecked() and len(raw["comp_flux"][0]) > 1:
                w = d.scatter_weights(raw["comp_flux"])
            rel, err = d.ensemble(raw["target_flux"], raw["target_flux_err"], raw["comp_flux"], raw["comp_flux_err"], w)
            lc |= {"rel_flux": rel.tolist(), "rel_flux_err": err.tolist()}
        lc["weights"] = None if w is None else w.tolist()
        if self.detrend_cfg:
            names, exclude, *rest = self.detrend_cfg
            cov = d.covariates(lc)
            degree = rest[0] if rest else 1
            out = d.detrend(lc["rel_flux"], {k: cov[k] for k in names}, exclude=exclude, time=lc["time"], degree=degree)
            lc |= {"rel_flux": out["rel_flux"], "detrend": out}
        lc["extra"] = []
        extras = [n for n in self._star_names() if n[1] != "comparison" and n[0] != "T1"]
        for i, (name, role, _) in enumerate(extras):
            if "extra_flux" not in raw or i >= len(raw["extra_flux"][0]):
                break
            f = [row[i] for row in raw["extra_flux"]]
            fe = [row[i] for row in raw["extra_flux_err"]]
            r, re_ = d.ensemble(f, fe, raw["comp_flux"], raw["comp_flux_err"], w)
            lc["extra"].append({"name": name, "role": role, "rel_flux": r.tolist(), "rel_flux_err": re_.tolist()})
        mags = self.known_comp_mags()
        if any(m is not None for m in mags):
            cat = (self.catalog or {}).get("comps") or []
            comps = []
            for i, m in enumerate(mags):  # catalogue colours are kept when the magnitude is the catalogue's
                c = cat[i] if i < len(cat) and cat[i] and m is not None and abs(cat[i]["mag"] - m) < 1e-6 else None
                comps.append(c if c else (None if m is None else {"mag": m}))
            colour = ((self.catalog or {}).get("target") or {}).get("colour")
            try:
                out = calibrate(lc, comps, colour)
            except ValueError:
                out = None
            if out:
                band = self.catalog["filter"] if self.catalog else self.band.currentText()
                lc |= {"mag": out["mag"], "mag_err": out["mag_err"], "mag_band": band, "mag_suspect": out["suspect"]}
                for x in lc["extra"]:
                    rel_x = np.asarray(x["rel_flux"])
                    xs = dict(lc) | {
                        "target_flux": (
                            rel_x * (np.asarray(raw["comp_flux"]) * (1 if w is None else w)).sum(axis=1)
                        ).tolist(),
                        "rel_flux": x["rel_flux"],
                        "rel_flux_err": x["rel_flux_err"],
                    }
                    xo = calibrate(xs, comps, None)
                    x |= {"mag": xo["mag"], "mag_err": xo["mag_err"]}
        self.light_curve = lc
        self._plot_current()
        self._summarise()

    def _saturated_frames(self, lc):
        sat = lc.get("saturation")
        if not sat or not lc.get("peak"):
            return np.zeros(len(lc["time"]), bool)
        return np.array([any(p is not None and p >= sat for p in row) for row in lc["peak"]])

    def _summarise(self):
        lc = self.light_curve
        f = np.asarray(lc["rel_flux"], float)
        lines = [self.tr("{n} points, scatter {rms:.2f} %").format(n=len(f), rms=100 * np.nanstd(f / np.nanmedian(f)))]
        a = lc.get("apertures") or {}
        if a.get("replaced"):
            lines.append(
                self.tr(
                    "The rings do not fit these small frames: aperture {r:.1f} px, sky {a:.1f}–{b:.1f} px, chosen "
                    "from the stars."
                ).format(r=a["r_ap"], a=a["r_in"], b=a["r_out"])
            )
        if self.excluded:
            lines.append(
                self.tr("{n} points deleted by hand (Restore deleted points brings them back).").format(
                    n=len(self.excluded)
                )
            )
        if lc.get("scintillation"):
            sc = 1085.7 * np.asarray(lc["scintillation"], float)
            lines.append(
                self.tr("Scintillation {lo:.1f}–{hi:.1f} mmag per frame is included in the errors.").format(
                    lo=np.nanmin(sc), hi=np.nanmax(sc)
                )
            )
        elif not np.size(lc.get("comp_flux", [])):  # space data (TESS, Kepler): no atmosphere to divide out
            lines.append(
                self.tr(
                    "No comparison star: the target's own flux over its median. Right for space data (TESS, Kepler); "
                    "from the ground, clouds and airmass stay in the light curve."
                )
            )
        elif "scintillation" in lc:
            lines.append(self.tr("Scintillation is not in the errors: give the telescope aperture (and the site)."))
        for x in lc["extra"]:
            r = np.asarray(x["rel_flux"], float)
            lines.append(
                self.tr("{name}: scatter {mmag:.1f} mmag").format(
                    name=x["name"], mmag=1000 * 1.0857 * np.nanstd(r / np.nanmedian(r))
                )
            )
        if lc.get("weights"):
            lines.append(
                self.tr("Weights: {w}").format(w=", ".join(f"C{i + 1} {v:.2f}" for i, v in enumerate(lc["weights"])))
            )
        if lc.get("detrend"):
            dt = lc["detrend"]
            lines.append(
                self.tr("Detrended ({k}): scatter of the {n} points fitted {a:.2f} % → {b:.2f} %").format(
                    k=", ".join(dt["coefficients"]),
                    n=dt["points_fitted"],
                    a=100 * dt["scatter_before"],
                    b=100 * dt["scatter_after"],
                )
            )
        for i in lc.get("mag_suspect") or []:
            lines.append(
                self.tr("C{i} disagrees with its known magnitude by more than 0.1 mag and was left out.").format(
                    i=i + 1
                )
            )
        sat = self._saturated_frames(lc)
        if sat.any():
            lines.append(
                self.tr("⚠ {n} frames have a star at or above the saturation level (marked red).").format(
                    n=int(sat.sum())
                )
            )
        self.result.setText("\n".join(lines))

    def _plot_current(self):
        from ..photometry import differential as d

        lc = self.light_curve
        if lc is None:
            return
        what = self.show_what.currentData() or "rel"
        t = np.asarray(lc["time"], float)
        t_ref = np.floor(t.min())
        x = t - t_ref
        sat = self._saturated_frames(lc)
        self.plot.figure.clear()
        self._plotted = None
        if not getattr(self, "_click_hooked", False):
            self.plot.canvas.mpl_connect("button_press_event", self._plot_clicked)
            self._click_hooked = True
        ax = self.plot.figure.add_subplot()
        if what == "diff":
            label = self._plot_differential(ax, lc, x, sat)
        elif what in ("rel", "dmag", "mag") or what.startswith("extra"):
            src = lc if not what.startswith("extra") else lc["extra"][int(what[5:])]
            f, e = np.asarray(src["rel_flux"], float), np.asarray(src["rel_flux_err"], float)
            if what == "mag" and "mag" in lc:
                y, ye, label = (
                    np.asarray(lc["mag"], float),
                    np.asarray(lc["mag_err"], float),
                    self.tr("Magnitude ({band})").format(band=lc["mag_band"]),
                )
                ax.invert_yaxis()
            elif what in ("dmag", "mag"):
                y, ye = d.delta_mag(f, e)
                label = self.tr("Δm (target − comparison)")
                ax.invert_yaxis()
            else:
                med = np.nanmedian(f)
                y, ye, label = f / med, e / med, self.tr("Relative flux")
            ax.errorbar(x, y, ye, fmt=".", ms=3, lw=0.5, alpha=0.8)
            self._plotted = (ax, x, y)
            if sat.any():
                ax.plot(x[sat], y[sat], "o", mfc="none", color="#e5484d", ms=7)
        elif what == "comps":
            curves, scatter = d.comps_against_others(lc["comp_flux"], lc.get("weights"))
            for i, (c, s_) in enumerate(zip(curves, scatter, strict=True)):
                ax.plot(
                    x,
                    np.asarray(c) - self.spacing.value() * i,
                    ".",
                    ms=3,
                    label=f"C{i + 1} ({1000 * 1.0857 * s_:.1f} mmag)",
                )
            label = self.tr("Relative flux (offset)")
            ax.legend(fontsize=7)
        elif what == "all":
            curves = [("T1", lc["rel_flux"])] + [(xx["name"], xx["rel_flux"]) for xx in lc["extra"]]
            for i, (name, c) in enumerate(curves):
                c = np.asarray(c, float)
                ax.plot(x, c / np.nanmedian(c) - self.spacing.value() * i, ".", ms=3, label=name)
            label = self.tr("Relative flux (offset)")
            ax.legend(fontsize=7)
        else:
            cov = d.covariates(lc)
            for key in ("airmass", "sky", "fwhm", "x", "y"):
                if key in cov:
                    v = np.asarray(cov[key], float)
                    ax.plot(x, (v - np.nanmean(v)) / (np.nanstd(v) or 1), ".", ms=2, label=key)
            label = self.tr("Normalised value")
            ax.legend(fontsize=7)
        ax.set_xlabel(f"{lc['time_scale']} − {t_ref:.0f}")
        ax.set_ylabel(label)
        self.plot.draw()

    def _plot_differential(self, ax, lc, x, sat):
        """The classic differential plot: Δm of the target against the comparison (ensemble) and, offset from it,
        the check star against the same comparison — or C1 − C2 when there is no check star. A flat check curve
        says the comparison is constant; its scatter (mmag) is the precision the target can be trusted to."""
        from ..photometry import differential as d

        y, ye = d.delta_mag(np.asarray(lc["rel_flux"], float), np.asarray(lc["rel_flux_err"], float))
        y = y - np.nanmedian(y)
        ax.errorbar(x, y, ye, fmt=".", ms=3, lw=0.5, alpha=0.8, label=self.tr("T1 − comparison"))
        self._plotted = (ax, x, y)
        if sat.any():
            ax.plot(x[sat], y[sat], "o", mfc="none", color="#e5484d", ms=7)
        check = next((e for e in lc.get("extra", []) if e.get("role") == "check"), None)
        comp = np.asarray(lc.get("comp_flux") or [[]], float)
        if check is not None:
            k, _ = d.delta_mag(np.asarray(check["rel_flux"], float), np.asarray(check["rel_flux_err"], float))
            name = self.tr("{k} (check) − comparison").format(k=check["name"])
        elif comp.ndim == 2 and comp.shape[1] >= 2:
            with np.errstate(divide="ignore", invalid="ignore"):
                k = -2.5 * np.log10(comp[:, 0] / comp[:, 1])
            name = "C1 − C2"
        else:
            k = None
        if k is not None:
            k = k - np.nanmedian(k)
            rms = 1000 * np.nanstd(k)
            gap = max(self.spacing.value(), 4 * np.nanstd(y), 4 * np.nanstd(k), 0.02)
            ax.plot(x, k - gap, ".", ms=3, color="#8e8e93", label=f"{name}: {rms:.1f} mmag")  # above: axis inverted
        ax.invert_yaxis()
        ax.legend(fontsize=7, loc="best")
        return self.tr("Δm (mag)")

    def _plot_clicked(self, event):
        """With "Click a point to delete it": the point nearest the click (within 10 screen pixels) is left out."""
        if not (self.delete_mode.isChecked() and self._plotted and event.inaxes is self._plotted[0]):
            return
        ax, x, y = self._plotted
        pix = ax.transData.transform(np.column_stack([x, y]))
        dist = np.hypot(pix[:, 0] - event.x, pix[:, 1] - event.y)
        i = int(np.nanargmin(dist)) if np.isfinite(dist).any() else -1
        if i >= 0 and dist[i] < 10:
            self.delete_point(i)

    def delete_point(self, i):
        """Leave out the i-th point of the light curve now shown (and its frame from every result)."""
        self.edit(self.tr("delete a point"), self._exclude, self.excluded | {self._frame_ids[i]})

    def restore_points(self):
        self.edit(self.tr("restore deleted points"), self._exclude, set())

    def _exclude(self, frames):
        self.excluded = frames
        self._recompute()

    def _detrend(self):
        names = [k for k, b in self.trend_boxes.items() if b.isChecked()]
        if not names or self.lc_raw is None:
            self.result.setText(self.tr("Tick at least one quantity to detrend against."))
            return
        from ..photometry.differential import covariates

        missing = [k for k in names if k not in covariates(self.lc_raw)]
        if missing:
            self.result.setText(
                self.tr(
                    "Not in this light curve: {names} (FWHM needs ‘Radii follow the seeing’; "
                    "airmass needs the site and RA/Dec)."
                ).format(names=", ".join(missing))
            )
            return
        exclude = None
        try:
            if self.exclude_from.text().strip() and self.exclude_to.text().strip():
                exclude = (float(self.exclude_from.text()), float(self.exclude_to.text()))
        except ValueError:
            self.result.setText(self.tr("The left-out range must be two times (numbers)."))
            return
        self._set_detrend((names, exclude, self.trend_degree.value()))

    def _set_detrend(self, cfg):
        self.edit(self.tr("detrending") if cfg else self.tr("undo detrending"), self._apply_detrend, cfg)

    def _apply_detrend(self, cfg):
        from .messages import translate

        old, self.detrend_cfg = self.detrend_cfg, cfg
        try:
            self._recompute()
        except ValueError as e:
            self.detrend_cfg = old
            self._recompute()
            self.result.setText(translate(str(e)))

    def _minimum(self):
        params = {"method": "kvw" if self.kvw.isChecked() else "trapezoid"}
        try:
            if self.t0.text().strip() and self.period.text().strip():
                params |= {"t0": float(self.t0.text()), "period": float(self.period.text())}
        except ValueError:
            self.result.setText(self.tr("T0 and period must be numbers."))
            return
        self.minimum_requested.emit(self.light_curve, params)

    def show_minimum(self, m):
        methods = {"kvw": self.tr("Kwee–van Woerden"), "trapezoid": self.tr("trapezoid fit")}
        if "minima" in m:  # every eclipse of a long series (TESS, several nights)
            ms = m["minima"]
            oc = np.array([x["o_minus_c"] for x in ms]) * 1440
            text = self.tr(
                "{n} minima timed ({p} primary, {s} secondary), {method}; O−C {mean:+.2f} min, scatter {sd:.2f} min"
            ).format(
                n=len(ms),
                p=sum(x["kind"] == "I" for x in ms),
                s=sum(x["kind"] == "II" for x in ms),
                method=methods[m["method"]],
                mean=float(np.mean(oc)),
                sd=float(np.std(oc)),
            )
            if m.get("skipped"):
                text += "\n" + self.tr("{n} predicted minima left out: not covered on both sides, or no dip.").format(
                    n=m["skipped"]
                )
            self.result.setText(text + "\n" + self.tr("All of them are on the O-C page."))
            if not self.plot.figure.axes or not self.light_curve:  # the plot was cleared meanwhile: nothing to mark
                return
            ax = self.plot.figure.axes[0]
            t_ref = np.floor(min(self.light_curve["time"]))
            for x in ms:
                ax.axvline(x["time"] - t_ref, color="red" if x["kind"] == "I" else "orange", lw=0.8)
            self.plot.draw()
            return
        text = self.tr("Minimum: {t:.6f} ± {e:.6f} {scale} ({e_min:.1f} min), {method}").format(
            t=m["time"], e=m["error"], scale=m["time_scale"], e_min=m["error"] * 1440, method=methods[m["method"]]
        )
        if "depth" in m:
            text += "\n" + self.tr("Depth {d:.2f} %, duration {h:.2f} h").format(
                d=100 * m["depth"], h=24 * m["duration"]
            )
        if "o_minus_c" in m:
            text += "\n" + self.tr("Epoch {n}, O−C = {oc:+.2f} min").format(n=m["epoch"], oc=m["o_minus_c"] * 1440)
        self.result.setText(text)
        if not self.plot.figure.axes or not self.light_curve:  # (an intermittent CI failure)
            return
        ax = self.plot.figure.axes[0]
        t_ref = np.floor(min(self.light_curve["time"]))
        ax.axvline(m["time"] - t_ref, color="red", lw=1)
        self.plot.draw()

    def _export_aavso(self):
        from ..brand import BRAND
        from ..photometry.export import aavso_extended

        dialog = AavsoDialog(len(self.comps), self)
        mags = self.known_comp_mags()
        if mags and all(m is not None for m in mags):
            dialog.mags.setText(", ".join(f"{m:.3f}" for m in mags))
        if self.catalog:
            dialog.filter.setCurrentText(self.catalog["filter"])
        checks = [x for x in self.light_curve.get("extra", []) if x["role"] == "check"]
        if checks:
            dialog.check.setText(checks[0]["name"])
        if dialog.exec() != QDialog.Accepted:
            return
        extra = {}
        if checks:  # the first check star goes into KNAME / KMAG
            extra = {"check": checks[0]["rel_flux"], "check_name": dialog.check.text().strip() or checks[0]["name"]}
        try:
            text = aavso_extended(self.light_curve, software_name=BRAND.display_name, **dialog.values(), **extra)
        except ValueError as e:
            QMessageBox.warning(self, self.tr("AAVSO report"), translate(e))
            return
        path, _ = QFileDialog.getSaveFileName(self, self.tr("AAVSO report"), "aavso.txt", "Text (*.txt)")
        if path:
            Path(path).write_text(text, encoding="utf-8")

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Export light curve"), "lightcurve.csv", "CSV (*.csv)")
        if path:
            export_csv(self.light_curve, path)

    def _to_models(self, path=None):
        """The light curve as a CSV file (the user chooses where; next to the frames by default), opened on the
        Orbits & models page."""
        default = str(Path(self.images[0]).with_name("lightcurve.csv")) if self.images else "lightcurve.csv"
        path = path or QFileDialog.getSaveFileName(self, self.tr("Save the light curve for the model"), default,
                                                   "CSV (*.csv)")[0]  # fmt: skip
        if path:
            export_csv(self.light_curve, path)
            self.next_requested.emit("orbits", str(path))


class AavsoDialog(QDialog):
    """The fields an AAVSO Extended report needs that the light curve does not know."""

    FILTERS = ("V", "B", "R", "I", "CV", "CR", "TG", "TB", "TR", "SG", "SR", "SI", "U")

    def __init__(self, n_comps, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("AAVSO report"))
        form = QFormLayout(self)
        self.star, self.obscode, self.mags = QLineEdit(self), QLineEdit(self), QLineEdit(self)
        self.chart, self.notes = QLineEdit(self), QLineEdit(self)
        self.filter = QComboBox(self)
        self.filter.addItems(self.FILTERS)
        self.mags.setPlaceholderText(self.tr("{n} values, e.g. 11.20, 11.85").format(n=n_comps))
        self.notes.setToolTip(self.tr("Anything a reader of the data should know (clouds, Moon, instrument)"))
        self.chart.setToolTip(self.tr("The identifier of the AAVSO chart (VSP) the comparison magnitudes come from"))
        self.filter.setToolTip(self.tr("Filter of the images, as AAVSO names it (CV: unfiltered, reduced to V)"))
        self.obscode.setToolTip(self.tr("Your AAVSO observer code"))
        self.star.setToolTip(self.tr("The variable's name as in AAVSO's VSX, e.g. AI DRA"))
        self.mags.setToolTip(
            self.tr("The comparison stars' magnitudes from the AAVSO chart (VSP), in the order the stars were marked")
        )
        form.addRow(self.tr("Star name (AAVSO VSX)"), self.star)
        form.addRow(self.tr("Observer code"), self.obscode)
        form.addRow(self.tr("Filter"), self.filter)
        form.addRow(self.tr("Catalogue magnitudes of the comparison stars"), self.mags)
        self.check = QLineEdit(self)
        self.check.setPlaceholderText(self.tr("label on the chart, e.g. 123"))
        self.check.setToolTip(
            self.tr(
                "The first check star's label on the chart; its magnitude goes into the report as a test of"
                " the comparison stars"
            )
        )
        form.addRow(self.tr("Check star (KNAME)"), self.check)
        form.addRow(self.tr("Chart ID"), self.chart)
        form.addRow(self.tr("Notes"), self.notes)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        mags = [float(v) for v in self.mags.text().replace(";", ",").split(",") if v.strip()]
        return {
            "star_name": self.star.text().strip(),
            "obscode": self.obscode.text().strip().upper(),
            "filt": self.filter.currentText(),
            "comp_mags": mags,
            "chart": self.chart.text().strip() or "na",
            "notes": self.notes.text().strip().replace(",", ";") or "na",
        }


def _without_frames(lc, excluded):
    """The light curve without the frames whose indices are in excluded: every per-frame list is filtered.
    Returns it and the original index of each kept frame."""
    n = len(lc["time"])
    keep = [i for i in range(n) if i not in excluded]
    if len(keep) == n:
        return lc, keep
    out = {k: [v[i] for i in keep] if isinstance(v, list) and len(v) == n else v for k, v in lc.items()}
    return out, keep


def export_csv(lc, path):
    """Light curve table as CSV (time, relative flux, error, raw fluxes)."""
    from astropy.table import Table

    t = Table(
        {
            lc["time_scale"]: lc["time"],
            "rel_flux": lc["rel_flux"],
            "rel_flux_err": lc["rel_flux_err"],
            "target_flux": lc["target_flux"],
            "file": lc["file"],
        }
    )
    for i, col in enumerate(np.asarray(lc["comp_flux"]).T):
        t[f"comp{i + 1}_flux"] = col
    if "airmass" in lc:
        t["airmass"] = lc["airmass"]
    from ..photometry.differential import delta_mag

    t["delta_mag"], t["delta_mag_err"] = delta_mag(lc["rel_flux"], lc["rel_flux_err"])
    if "mag" in lc:  # magnitudes from known (typed-in or catalogue) comparison magnitudes
        t[f"{lc['mag_band']}_mag"], t[f"{lc['mag_band']}_mag_err"] = lc["mag"], lc["mag_err"]
    for x in lc.get("extra") or []:  # check stars and further targets against the same ensemble
        t[f"{x['name']}_rel_flux"], t[f"{x['name']}_rel_flux_err"] = x["rel_flux"], x["rel_flux_err"]
        if "mag" in x:
            t[f"{x['name']}_mag"], t[f"{x['name']}_mag_err"] = x["mag"], x["mag_err"]
    if lc.get("fwhm"):
        t["fwhm"] = lc["fwhm"]
    t.write(path, format="csv", overwrite=True)
    return path


def _decimals(err):
    """Decimals that show a value to the second significant digit of its error."""
    return max(0, 1 - int(np.floor(np.log10(err)))) if err > 0 and np.isfinite(err) else 4


class OCPage(QWidget):
    """Minimum times -> epochs, linear or quadratic ephemeris, O-C diagram."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fit_result = None
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        lay.addWidget(_title(self.tr("Light curves & O-C"), self))
        lay.addWidget(QLabel(self.tr("Minimum times, one per line: time [error] [I/II] [source]"), self))
        self.text = QPlainTextEdit(self)
        self.text.setPlaceholderText("2455867.40274 0.00005 I  literature\n2458107.71232 0.0033 I  this work")
        lay.addWidget(self.text, 1)
        row = QHBoxLayout()
        load = QPushButton(self.tr("Load file…"), self)
        load.clicked.connect(self._load)
        row.addWidget(load)
        load.setToolTip(
            self.tr("A text file of times of minimum or maximum: time, error, type (I / II), source; one per line")
        )
        row.addStretch(1)
        lay.addLayout(row)
        grid = QGridLayout()
        self.t0 = QLineEdit(self)
        self.period = QLineEdit(self)
        grid.addWidget(QLabel(self.tr("Reference T0"), self), 0, 0)
        self.period.setToolTip(self.tr("Period of the ephemeris used to count the cycles; the fit improves it"))
        self.t0.setToolTip(self.tr("Epoch zero of the ephemeris (BJD or HJD, as the times); empty: the first minimum"))
        grid.addWidget(self.t0, 0, 1)
        grid.addWidget(QLabel(self.tr("Period (d)"), self), 1, 0)
        grid.addWidget(self.period, 1, 1)
        lay.addLayout(grid)
        self.linear = QRadioButton(self.tr("Linear ephemeris"), self)
        self.linear.setToolTip(self.tr("A constant period: O−C on a straight line (corrects T0 and the period)"))
        self.quadratic = QRadioButton(self.tr("Quadratic (period change)"), self)
        self.quadratic.setToolTip(
            self.tr("A steadily changing period (mass transfer, mass loss): O−C on a parabola; gives dP/dt")
        )
        self.ltte = QRadioButton(self.tr("Third body (light-travel time)"), self)
        self.ltte.setToolTip(
            self.tr(
                "A third star moves the pair around: O−C waves with the third body's orbit (Irwin 1952); "
                "needs minima over more than one cycle of the wave"
            )
        )
        self.apsidal = QRadioButton(self.tr("Apsidal motion (eccentric orbit, primary and secondary)"), self)
        self.apsidal.setToolTip(
            self.tr(
                "An eccentric orbit turns: primary and secondary minima drift in opposite directions; needs"
                " both kinds of minimum (type I and II)"
            )
        )
        self.linear.setChecked(True)
        for b in (self.linear, self.quadratic, self.ltte, self.apsidal):
            lay.addWidget(b)
        row = QHBoxLayout()
        self.use_mcmc = QCheckBox(self.tr("MCMC uncertainties (slower, for correlated parameters)"), self)
        self.use_mcmc.setToolTip(
            self.tr(
                "After the fit, a Markov chain (emcee) explores the third-body or apsidal parameters: 68 % "
                "intervals of every parameter, e and ω included, when they depend on each other. A linear or "
                "quadratic ephemeris is a linear problem: its least-squares errors are already exact."
            )
        )
        self.mcmc_steps = QSpinBox(self)
        self.mcmc_steps.setRange(200, 20000)
        self.mcmc_steps.setSingleStep(500)
        self.mcmc_steps.setValue(2000)
        self.mcmc_steps.setSuffix(self.tr(" steps"))
        self.mcmc_steps.setToolTip(self.tr("Length of the Markov chain; more steps give steadier errors"))
        row.addWidget(self.use_mcmc, 1)
        row.addWidget(self.mcmc_steps)
        lay.addLayout(row)

        def mcmc_allowed():
            self.use_mcmc.setEnabled(self.ltte.isChecked() or self.apsidal.isChecked())
            self.mcmc_steps.setEnabled(self.use_mcmc.isEnabled())

        for b in (self.linear, self.quadratic, self.ltte, self.apsidal):
            b.toggled.connect(mcmc_allowed)
        mcmc_allowed()
        self.fit_button = QPushButton(self.tr("Fit and draw O-C"), self)
        self.fit_button.clicked.connect(self.run_fit)
        self.fit_button.setToolTip(
            self.tr("Fits the chosen model to the times and draws O−C (observed minus calculated) against cycle number")
        )
        lay.addWidget(self.fit_button)
        from .export import results_button

        self.fit_result = None
        self.background = None  # set by the main window: runs the MCMC as a task
        lay.addWidget(results_button(self, self.fit_table))
        self.result = QLabel(self)
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.result)
        split.addWidget(left)
        self.plot = PlotCanvas(self)
        split.addWidget(self.plot)
        split.setSizes([380, 800])
        QVBoxLayout(self).addWidget(split)

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("Load minimum times"), "", self.tr("Text (*.txt *.csv *.dat);;All (*)")
        )
        if path:
            self.text.setPlainText(Path(path).read_text(encoding="utf-8", errors="replace"))

    def add_minimum(self, time, error, source="", kind="I"):
        self.text.appendPlainText(f"{time:.6f} {error:.6f} {kind} {source}".rstrip())

    def fit_table(self):
        """(rows, caption) of the last O−C fit for the results export."""
        f = self.fit_result
        if f is None:
            self.result.setText(self.tr("Fit the O−C diagram first."))
            return None
        n = len(f.epochs)
        if hasattr(f, "p3"):  # light-travel time
            e = f.errors
            rows = [
                ("T0", f.t0, e["t0"], "d"),
                ("P", f.period, e["period"], "d"),
                ("A (semi-amplitude)", f.amplitude * 1440, e["amplitude"] * 1440, "min"),
                ("P3", f.p3 / 365.25, e["p3"] / 365.25, "yr"),
                ("T3 (periastron)", f.t3, e["t3"], "d"),
                ("e3", f.e, e.get("e"), ""),
                ("omega3", f.omega, e.get("omega"), "deg"),
                ("f(m3)", f.mass_function, e.get("f_m3"), "Msun"),
            ]
            model = self.tr("light-travel time in a third-body orbit (Irwin 1952)")
        elif hasattr(f, "d_omega"):  # apsidal motion
            rows = [
                ("T0", f.t0, f.errors["t0"], "d"),
                ("Ps (sidereal)", f.period, f.errors["period"], "d"),
                ("e", f.e, f.errors.get("e"), ""),
                ("omega0", f.omega0, f.errors.get("omega0"), "deg"),
                ("d omega / dE", f.d_omega, f.errors["d_omega"], "deg/cycle"),
                ("U", f.u_years, f.errors.get("u_years"), "yr"),
            ]
            model = self.tr("apsidal motion of an eccentric orbit")
        else:
            rows = [("T0", f.t0, f.t0_err, "d"), ("P", f.period, f.period_err, "d")]
            if f.order == 2:
                rows += [("Q", f.q, f.q_err, "d"), ("dP/dt", f.dp_dt, f.dp_dt_err, "s/yr")]
            model = self.tr("quadratic ephemeris") if f.order == 2 else self.tr("linear ephemeris")
        rows.append(("chi2_r", f.chi2r, None, ""))
        caption = self.tr(
            "O−C fit to {n} times of minimum: {model}; weighted least squares, 1σ errors (scaled by √χ²ᵣ when χ²ᵣ > 1)."
        ).format(n=n, model=model)
        if getattr(f, "mcmc", None):
            caption += " " + self.tr("Errors: the larger side of the MCMC 68 % intervals (emcee, {s} steps).").format(
                s=self.mcmc_steps.value()
            )
        return rows, caption

    def run_fit(self):
        from ..timeseries.ephemeris import fit, parse_minima
        from ..timeseries.oc_models import fit_apsidal, fit_ltte
        from .messages import translate

        try:
            t0, period = float(self.t0.text()), float(self.period.text())
        except ValueError:
            self.result.setText(self.tr("Give the reference T0 and the period in days."))
            return None
        try:
            minima = parse_minima(self.text.toPlainText())
            steps = self.mcmc_steps.value() if self.use_mcmc.isChecked() and self.use_mcmc.isEnabled() else 0
            model = "ltte" if self.ltte.isChecked() else "apsidal" if self.apsidal.isChecked() else None
            if steps and self.background:  # the chain runs as a task: the page stays usable, Tasks can cancel it
                self.result.setText(self.tr("Fitting, then the MCMC ({s} steps) runs as a task…").format(s=steps))
                self.background(model, self.text.toPlainText(), t0, period, steps, minima)
                return None
            if model == "ltte":
                f = fit_ltte(minima, t0, period, mcmc_steps=steps)
            elif model == "apsidal":
                f = fit_apsidal(minima, t0, period, mcmc_steps=steps)
            else:
                f = fit(minima, t0, period, order=2 if self.quadratic.isChecked() else 1)
        except ValueError as e:
            self.result.setText(self.tr("Cannot fit: {error}").format(error=translate(str(e))))
            return None
        return self.show_fit(f, minima)

    def show_fit(self, f, minima):
        """Draw a fit (also the result of the background task) and write its numbers."""
        self.fit_result = f
        if not hasattr(f, "order"):
            return self._show_oc_model(f, minima)
        lines = [
            self.tr("T0 = {t0:.6f} ± {e:.6f}").format(t0=f.t0, e=f.t0_err),
            self.tr("P = {p:.8f} ± {e:.8f} d").format(p=f.period, e=f.period_err),
        ]
        if f.order == 2:
            lines.append(
                self.tr("Q = {q:.3e} ± {e:.1e} d, dP/dt = {dp:.3g} ± {dpe:.2g} s/yr").format(
                    q=f.q, e=f.q_err, dp=f.dp_dt, dpe=f.dp_dt_err
                )
            )
        lines.append(self.tr("χ²ᵣ = {c:.2f}, {n} minima").format(c=f.chi2r, n=len(minima)))
        self.result.setText("\n".join(lines))
        errs = np.array([m.error or np.nan for m in minima])
        self.plot.figure.clear()
        ax, ax2 = self.plot.figure.subplots(2, 1, sharex=True, height_ratios=[3, 1])
        prim = np.array([m.kind == "I" for m in minima])
        for sel, label, mk in ((prim, self.tr("primary"), "o"), (~prim, self.tr("secondary"), "s")):
            if sel.any():
                ax.errorbar(f.epochs[sel], f.o_minus_c[sel] * 1440, errs[sel] * 1440, fmt=mk, ms=4, label=label)
        e_line = np.linspace(f.epochs.min(), f.epochs.max(), 200)
        ax.plot(e_line, f.model_o_minus_c(e_line) * 1440, "r-", lw=1)
        ax.set_ylabel(self.tr("O−C (min)"))
        ax.legend(fontsize="small")
        ax2.errorbar(f.epochs, f.residuals * 1440, errs * 1440, fmt=".", ms=3)
        ax2.axhline(0, color="r", lw=1)
        ax2.set_xlabel(self.tr("Epoch"))
        ax2.set_ylabel(self.tr("Residual (min)"))
        self.plot.draw()
        return f

    def _oc_model_text(self, f, n):
        if hasattr(f, "p3"):
            return [
                self.tr(
                    "Third body: P3 = {p:.2f} ± {pe:.2f} yr, A = {a:.2f} ± {ae:.2f} min, e = {e:.2f}, ω = {w:.0f}°"
                ).format(
                    p=f.p3 / 365.25,
                    pe=f.errors["p3"] / 365.25,
                    a=f.amplitude * 1440,
                    ae=f.errors["amplitude"] * 1440,
                    e=f.e,
                    w=f.omega,
                ),
                self.tr("f(m3) = {fm:.4f} M☉, T0 = {t0:.6f}, P = {p:.8f} d, χ²ᵣ = {c:.2f}, {n} minima").format(
                    fm=f.mass_function, t0=f.t0, p=f.period, c=f.chi2r, n=n
                ),
            ]
        return [
            self.tr(
                "Apsidal motion: e = {e:.4f}, ω0 = {w:.1f}°, dω/dE = {dw:.5f} ± {dwe:.5f} °/cycle, U = {u:.1f} yr"
            ).format(e=f.e, w=f.omega0, dw=f.d_omega, dwe=f.errors["d_omega"], u=f.u_years),
            self.tr("T0 = {t0:.6f}, Ps = {p:.8f} d, χ²ᵣ = {c:.2f}, {n} minima").format(
                t0=f.t0, p=f.period, c=f.chi2r, n=n
            ),
        ]

    def _show_oc_model(self, f, minima):
        """Third body or apsidal motion: the curve(s) over the O-C points, residuals below."""
        lines = self._oc_model_text(f, len(minima))
        if f.mcmc:
            p = f.mcmc["params"]
            shown = [("e", "e", 1), ("ω", "omega", 1), ("ω0", "omega0", 1), ("U", "u_years", 1)]
            shown += [("P3", "p3", 1 / 365.25), ("A", "amplitude", 1440), ("f(m3)", "f_m3", 1)]
            lines.append(
                self.tr("MCMC (acceptance {a:.2f}): ").format(a=f.mcmc["acceptance"])
                + ", ".join(
                    f"{label} = {p[k][0] * u:.{_decimals(min(p[k][1:]) * u)}f} −{p[k][1] * u:.2g} +{p[k][2] * u:.2g}"
                    for label, k, u in shown
                    if k in p
                )
            )
        self.result.setText("\n".join(lines))
        errs = np.array([m.error or np.nan for m in minima])
        prim = np.array([m.kind == "I" for m in minima])
        self.plot.figure.clear()
        ax, ax2 = self.plot.figure.subplots(2, 1, sharex=True, height_ratios=[3, 1])
        e_line = np.linspace(f.epochs.min(), f.epochs.max(), 600)
        for sel, label, mk, kind in ((prim, self.tr("primary"), "o", "I"), (~prim, self.tr("secondary"), "s", "II")):
            if sel.any():
                ax.errorbar(f.epochs[sel], f.o_minus_c[sel] * 1440, errs[sel] * 1440, fmt=mk, ms=4, label=label)
                ax.plot(e_line, f.model_o_minus_c(e_line, kind) * 1440, lw=1)
        ax.set_ylabel(self.tr("O−C (min)"))
        ax.legend(fontsize="small")
        ax2.errorbar(f.epochs, f.residuals * 1440, errs * 1440, fmt=".", ms=3)
        ax2.axhline(0, color="r", lw=1)
        ax2.set_xlabel(self.tr("Epoch"))
        ax2.set_ylabel(self.tr("Residual (min)"))
        self.plot.draw()
        return f


class PeriodPage(Undoable, QWidget):
    """Period search on a light curve (from the Photometry page or a CSV file) and phase folding."""

    search_requested = Signal(list, list, dict)  # time, flux, params
    archive_requested = Signal(str, str)  # target, mission

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_undo()
        self.time, self.flux, self.best, self.periodogram = None, None, None, None
        self.err = None  # the points' errors when the light curve has them (error bars, weights of the search)
        split = QSplitter(Qt.Horizontal, self)
        left = QWidget(self)
        lay = QVBoxLayout(left)
        self.source = QLabel(
            self.tr("No light curve yet: measure one on the Photometry page or load a CSV file."), self
        )
        self.source.setWordWrap(True)
        lay.addWidget(self.source)
        load = QPushButton(self.tr("Load CSV (time, flux; or AAVSO / ZTF / ASAS-SN files)…"), self)
        load.setToolTip(
            self.tr(
                "Any table with a time column and a brightness column; files downloaded from AAVSO, ZTF and"
                " ASAS-SN are recognised"
            )
        )
        load.clicked.connect(self._load)
        save = QPushButton(self.tr("Save light curve (CSV)…"), self)
        save.setToolTip(
            self.tr(
                "The light curve as shown (downloaded, edited) in a CSV file: open it on the Orbits & models page "
                "or in another program"
            )
        )
        save.clicked.connect(self._save)
        row = QHBoxLayout()
        row.addWidget(load, 1)
        row.addWidget(save)
        lay.addLayout(row)
        row = QHBoxLayout()
        self.archive_target = QLineEdit(self)
        self.archive_target.setPlaceholderText(self.tr("star name, e.g. AI Dra or TIC 12345678"))
        self.archive_target.setToolTip(
            self.tr("The star's name or catalogue number as the archive knows it; Enter starts the download")
        )
        self.mission = QComboBox(self)
        self.mission.addItems(("TESS", "Kepler", "K2", "ZTF", "AAVSO"))
        self.mission.setToolTip(self.tr("The archive to download the light curve from"))
        fetch = QPushButton(self.tr("Download"), self)
        fetch.setToolTip(
            self.tr("TESS / Kepler / K2 from MAST, ZTF from IRSA, AAVSO observations (needs the internet)")
        )
        fetch.clicked.connect(self._fetch)
        self.archive_target.returnPressed.connect(self._fetch)
        for w in (self.archive_target, self.mission, fetch):
            row.addWidget(w)
        lay.addLayout(row)
        grid = QGridLayout()
        self.method = QComboBox(self)
        self.method.addItem(self.tr("Lomb–Scargle (pulsating stars)"), "lomb-scargle")
        self.method.addItem(self.tr("BLS (transits, Algol-type eclipses)"), "bls")
        self.method.addItem(self.tr("PDM (any shape)"), "pdm")
        self.method.addItem(self.tr("ANOVA (multi-harmonic, any smooth shape)"), "anova")
        for i, about in enumerate(
            (
                self.tr("Fits a sine wave at every trial period; the power is the share of the variance the sine "
                        "explains (Lomb 1976, Scargle 1982)."),
                self.tr("Fits a box-shaped dip (depth, duration, phase) at every trial period (Kovács, Zucker & "
                        "Mazeh 2002)."),
                self.tr("Folds the data on every trial period and compares the scatter inside phase bins with the "
                        "total scatter (Stellingwerf 1978)."),
                self.tr("Fits a Fourier series of two harmonics at every trial period; the F statistic of that fit "
                        "(Schwarzenberg-Czerny 1996)."),
            )
        ):  # fmt: skip
            self.method.setItemData(i, about, Qt.ToolTipRole)
        self.method.setToolTip(
            self.tr(
                "Lomb–Scargle: sine-like curves (pulsations, spots); BLS: short, box-shaped dips; PDM and "
                "ANOVA: curves of any shape, e.g. eclipsing binaries with two minima. The formulas: Guide, "
                "Mathematics of the methods"
            )
        )
        self.p_min, self.p_max = QDoubleSpinBox(self), QDoubleSpinBox(self)
        for w, v in ((self.p_min, 0.05), (self.p_max, 10.0)):
            w.setDecimals(4)
            w.setRange(0.001, 10000)
            w.setValue(v)
        grid.addWidget(QLabel(self.tr("Method"), self), 0, 0)
        grid.addWidget(self.method, 0, 1)
        grid.addWidget(QLabel(self.tr("Shortest period (d)"), self), 1, 0)
        grid.addWidget(self.p_min, 1, 1)
        self.p_min.setToolTip(
            self.tr("Shortest period searched; shorter than twice the time between points cannot be found")
        )
        grid.addWidget(QLabel(self.tr("Longest period (d)"), self), 2, 0)
        grid.addWidget(self.p_max, 2, 1)
        self.p_max.setToolTip(self.tr("Longest period searched; the data should cover at least two cycles of it"))
        from PySide6.QtWidgets import QSpinBox

        self.phase_bins = QSpinBox(self)
        self.phase_bins.setRange(0, 1000)
        self.phase_bins.setValue(0)
        self.phase_bins.setSpecialValueText(self.tr("off"))
        self.phase_bins.setToolTip(self.tr("Mean curve in this many phase bins on the folded plot"))
        self.phase_bins.valueChanged.connect(lambda _: self.best and self._plot_phase())
        grid.addWidget(QLabel(self.tr("Phase bins"), self), 3, 0)
        grid.addWidget(self.phase_bins, 3, 1)
        lay.addLayout(grid)
        edit = QGridLayout()
        self.clip_sigma = QDoubleSpinBox(self)
        self.clip_sigma.setRange(1.0, 20.0)
        self.clip_sigma.setValue(4.0)
        self.clip_sigma.setToolTip(self.tr("Limit in standard deviations for Remove outliers"))
        clip = QPushButton(self.tr("Remove outliers (σ)"), self)
        clip.clicked.connect(lambda: self.edit(self.tr("remove outliers"), self._clip))
        clip.setToolTip(
            self.tr(
                "Removes points further than this many standard deviations from the median of their "
                "neighbours in time (cosmic rays, bad frames); Ctrl+Z brings them back"
            )
        )
        self.bin_minutes = QDoubleSpinBox(self)
        self.bin_minutes.setRange(0.1, 10000)
        self.bin_minutes.setValue(5.0)
        self.bin_minutes.setToolTip(self.tr("Length of a time bin in minutes for Bin in time"))
        binb = QPushButton(self.tr("Bin in time (min)"), self)
        binb.clicked.connect(lambda: self.edit(self.tr("bin in time"), self._bin))
        binb.setToolTip(
            self.tr(
                "Averages the points in time bins of this length: less noise, fewer points; keep the bins "
                "much shorter than an eclipse"
            )
        )
        self.delete_mode = QPushButton(self.tr("Delete points by clicking"), self)
        self.delete_mode.setCheckable(True)
        self.delete_mode.setToolTip(self.tr("Click a point on the light-curve plot to remove it"))
        units = QPushButton(self.tr("Flux ↔ magnitude"), self)
        units.clicked.connect(lambda: self.edit(self.tr("flux / magnitude"), self._convert))
        units.setToolTip(self.tr("Converts relative flux to magnitudes (−2.5 log) or back"))
        undo = QPushButton(self.tr("Undo edits"), self)
        undo.clicked.connect(lambda: self.edit(self.tr("undo edits"), self._undo))
        undo.setToolTip(self.tr("Back to the light curve as it was loaded (Ctrl+Z takes back one step at a time)"))
        edit.addWidget(clip, 0, 0)
        edit.addWidget(self.clip_sigma, 0, 1)
        edit.addWidget(binb, 1, 0)
        edit.addWidget(self.bin_minutes, 1, 1)
        edit.addWidget(self.delete_mode, 2, 0)
        edit.addWidget(units, 2, 1)
        edit.addWidget(undo, 3, 0)
        lay.addLayout(edit)
        self.search_button = QPushButton(self.tr("Search"), self)
        self.search_button.setEnabled(False)
        self.search_button.clicked.connect(self._search)
        self.search_button.setToolTip(
            self.tr(
                "Computes the periodogram between the shortest and longest period and folds the curve on "
                "the best period; check the folded plot by eye"
            )
        )
        lay.addWidget(self.search_button)
        self.result = QLabel(self)
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.result)
        lay.addStretch(1)
        split.addWidget(left)
        self.plot = PlotCanvas(self)
        self.plot.canvas.mpl_connect("button_press_event", self._clicked)
        split.addWidget(self.plot)
        split.setSizes([380, 800])
        QVBoxLayout(self).addWidget(split)
        self.original, self.magnitudes = None, False

    def _fetch(self):
        if self.archive_target.text().strip():
            source = {"ZTF": "IRSA", "AAVSO": "AAVSO"}.get(self.mission.currentText(), "MAST")
            self.source.setText(self.tr("Downloading from {source}…").format(source=source))
            self.archive_requested.emit(self.archive_target.text().strip(), self.mission.currentText())

    def undo_state(self):
        return {
            "time": self.time,
            "flux": self.flux,
            "err": self.err,
            "mag": self.magnitudes,
            "source": self.source.text(),
        }

    def set_undo_state(self, st):
        self.time, self.flux, self.magnitudes = st["time"], st["flux"], st["mag"]
        self.err = st.get("err")
        self.source.setText(st["source"])
        self.search_button.setEnabled(bool(self.time) and len(self.time) > 10)
        self._plot_light_curve()

    def set_light_curve(self, time, flux, label, keep_original=False, err=None):
        """err: the points' errors (same units as flux), drawn as error bars and used as weights by Lomb–Scargle and
        BLS; None when the source has none."""
        self.time, self.flux = list(time), list(flux)
        ok = err is not None and len(err) == len(self.time) and np.all(np.isfinite(np.asarray(err, float)))
        self.err = [float(e) for e in err] if ok and np.all(np.asarray(err, float) > 0) else None
        if not keep_original:
            self.undo_stack.clear()  # another star: the edits of the last one do not apply
            self.original, self.magnitudes, self.label = (self.time, self.flux, self.err), False, label
            self.best = None  # a new star: the old period does not apply
        self.source.setText(self.tr("{n} points from {source}").format(n=len(self.time), source=label))
        self.search_button.setEnabled(len(self.time) > 10)
        self._plot_light_curve()

    def _edited(self, t, y, what, err=None):
        e = None if err is None else np.asarray(err).tolist()
        self.set_light_curve(np.asarray(t).tolist(), np.asarray(y).tolist(), f"{self.label}, {what}", True, e)

    def _errs(self, idx=None):
        """The errors (of the points idx), or None."""
        if self.err is None:
            return None
        e = np.asarray(self.err, float)
        return e if idx is None else e[idx]

    def _clip(self):
        if self.time:
            keep = fourier_edit().sigma_clip(self.flux, self.clip_sigma.value(), self.time, self.best)
            t, y = np.asarray(self.time)[keep], np.asarray(self.flux)[keep]
            self._edited(t, y, self.tr("outliers removed"), self._errs(keep))

    def _bin(self):
        if self.time:
            binned = fourier_edit().bin_time(self.time, self.flux, self.bin_minutes.value() / 1440, self._errs())
            self._edited(*binned[:2], self.tr("binned"), binned[2] if len(binned) > 2 else None)

    def _convert(self):
        if self.time:
            f = fourier_edit()
            y = np.asarray(self.flux, float)
            if not self.magnitudes and np.any(y <= 0):
                self.source.setText(self.tr("Fluxes must be positive to convert to magnitudes."))
                return
            e = self._errs()
            self.magnitudes = not self.magnitudes
            if e is not None:  # σm = 1.0857 σF / F, and back
                e = 2.5 / np.log(10) * e / y if self.magnitudes else e * f.mag_to_flux(y) * np.log(10) / 2.5
            y = f.flux_to_mag(y) if self.magnitudes else f.mag_to_flux(y)
            self._edited(self.time, y, self.tr("magnitudes") if self.magnitudes else self.tr("flux"), e)

    def _undo(self):
        if self.original:
            self.magnitudes = False
            t, y, e = self.original
            self.set_light_curve(t, y, self.label, True, e)

    def _clicked(self, event):
        if not (self.delete_mode.isChecked() and self.time and event.inaxes is not None and event.xdata is not None):
            return
        ax = event.inaxes
        t, y = np.asarray(self.time), np.asarray(self.flux)
        x = t - ax._t_ref if getattr(ax, "_kind", "") == "time" else fold_phase(t, self.best, self._t0())
        if getattr(ax, "_kind", "") not in ("time", "phase"):
            return
        (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
        d = np.hypot((x - event.xdata) / (x1 - x0), (y - event.ydata) / (y1 - y0))
        i = int(np.argmin(d))
        if d[i] < 0.02:
            e = None if self.err is None else np.delete(np.asarray(self.err), i)
            self.edit(
                self.tr("delete a point"), self._edited, np.delete(t, i), np.delete(y, i), self.tr("points deleted"), e
            )

    def _t0(self):
        t, f = np.asarray(self.time), np.asarray(self.flux)
        return t[np.argmax(f) if self.magnitudes else np.argmin(f)]

    def _plot_light_curve(self):
        if self.best:
            return self._plot_phase()
        self.plot.figure.clear()
        ax = self.plot.figure.subplots()
        ax._kind = "time"
        t = np.asarray(self.time)
        ax._t_ref = float(np.floor(t.min())) if t.size and t.min() > 1000 else 0.0  # JD: "+2.46e6" says nothing
        if self.err is not None:
            ax.errorbar(t - ax._t_ref, self.flux, self.err, fmt=".", ms=2, lw=0.5, elinewidth=0.5, alpha=0.8)
        else:
            ax.plot(t - ax._t_ref, self.flux, ".", ms=2)
        ax.set_xlabel(self.tr("Time − {t:.0f} (d)").format(t=ax._t_ref) if ax._t_ref else self.tr("Time (d)"))
        ax.set_ylabel(self.tr("Magnitude") if self.magnitudes else self.tr("Relative flux"))
        if self.magnitudes:
            ax.invert_yaxis()
        self.plot.draw()

    def _load(self):
        path, _ = QFileDialog.getOpenFileName(self, self.tr("Load light curve"), "", "CSV (*.csv *.txt *.dat)")
        if not path:
            return
        from ..timeseries import surveys

        try:
            rows = surveys.parse(Path(path).read_text(encoding="utf-8", errors="replace"))
        except (OSError, ValueError, UnicodeError):
            rows = []
        if len(rows) >= 3:  # a survey or database export: one band, magnitudes as relative flux
            try:
                lc = surveys.to_light_curve(rows)
                return self.set_light_curve(
                    lc["time"], lc["rel_flux"], f"{Path(path).name} ({lc['band']})", err=lc.get("rel_flux_err")
                )
            except ValueError:
                pass  # not enough points in one band: read it as a plain table
        try:
            data = np.genfromtxt(
                path,
                delimiter="," if path.endswith(".csv") else None,
                names=None,
                skip_header=1 if not Path(path).read_text().lstrip()[:1].isdigit() else 0,
            )
            err = data[:, 2] if data.ndim == 2 and data.shape[1] >= 3 else None  # a third column: the errors
            self.set_light_curve(data[:, 0], data[:, 1], Path(path).name, err=err)
        except (ValueError, IndexError) as e:
            self.source.setText(self.tr("Cannot read {file}: {error}").format(file=Path(path).name, error=translate(e)))

    def save_csv(self, path):
        """Time and flux (or magnitude) columns that the Orbits & models page reads back."""
        column = "mag" if self.magnitudes else "rel_flux"
        if self.err is not None:
            rows = "\n".join(f"{t:.7f},{y:.7g},{e:.3g}" for t, y, e in zip(self.time, self.flux, self.err, strict=True))
            Path(path).write_text(f"time,{column},{column}_err\n{rows}\n", encoding="utf-8")
            return
        rows = "\n".join(f"{t:.7f},{y:.7g}" for t, y in zip(self.time, self.flux, strict=True))
        Path(path).write_text(f"time,{column}\n{rows}\n", encoding="utf-8")

    def _save(self):
        if not self.time:
            self.source.setText(self.tr("No light curve to save yet."))
            return
        name = "".join(c if c.isalnum() or c in "-_" else "_" for c in self.label.split(" (")[0])[:60]
        path, _ = QFileDialog.getSaveFileName(self, self.tr("Save light curve"), f"{name}.csv", "CSV (*.csv)")
        if path:
            self.save_csv(path)
            self.source.setText(self.tr("Saved {n} points to {file}").format(n=len(self.time), file=Path(path).name))

    def _search(self):
        self.result.setText(self.tr("Searching…"))
        params = {"method": self.method.currentData(), "p_min": self.p_min.value(), "p_max": self.p_max.value()}
        if self.err is not None:
            params["err"] = self.err  # an input of the step (main window), not a parameter
        self.search_requested.emit(self.time, self.flux, params)

    def show_result(self, out):
        self.best, self.periodogram = out["best"], out
        text = self.tr("Best period: {p:.6f} d").format(p=self.best)
        t = np.sort(self.time)
        cuts = np.flatnonzero(np.diff(t) > 20 * self.best) + 1  # stretches (seasons, sectors) apart
        if len(cuts):  # the cycle count across the widest gap is not certain: centre to centre of its sides
            i = int(np.argmax(t[cuts] - t[cuts - 1]))
            before = t[(cuts[i - 1] if i else 0) : cuts[i]]
            after = t[cuts[i] : (cuts[i + 1] if i + 1 < len(cuts) else len(t))]
            gap = float(np.mean(after) - np.mean(before))
            f, df = 1 / self.best, 1 / gap
            text += "\n" + self.tr(
                "The data come in stretches {g:.0f} d apart: one cycle more or less across the gap ({p1:.6f} or "
                "{p2:.6f} d) fits almost as well. Check with the times of minimum (O−C)."
            ).format(g=gap, p1=1 / (f + df), p2=1 / (f - df) if f > df else float("inf"))
        self.result.setText(text)
        self._plot_phase()

    def _plot_phase(self):
        out = self.periodogram
        self.plot.figure.clear()
        ax, ax2 = self.plot.figure.subplots(2, 1)
        ax.plot(out["periods"], out["power"], lw=0.7)
        ax.axvline(self.best, color="r", lw=0.8)
        ax.set_xscale("log")
        ax.set_xlabel(self.tr("Period (d)"))
        ax.set_ylabel(self.tr("Power"))
        t, f = np.asarray(self.time), np.asarray(self.flux)
        ph = fold_phase(t, self.best, self._t0())
        ax2._kind = "phase"
        alpha = 0.5 if self.phase_bins.value() else 1
        if self.err is not None:
            ax2.errorbar(ph, f, self.err, fmt=".", ms=2, lw=0.5, elinewidth=0.5, alpha=alpha)
        else:
            ax2.plot(ph, f, ".", ms=2, alpha=alpha)
        if self.phase_bins.value():
            c, mean, err, _ = fourier_edit().bin_phase(ph, f, self.phase_bins.value())
            ax2.errorbar(c, mean, err, fmt="o", ms=3, color="C3", lw=0.8)
        ax2.set_xlabel(self.tr("Phase"))
        ax2.set_ylabel(self.tr("Magnitude") if self.magnitudes else self.tr("Relative flux"))
        if self.magnitudes:
            ax2.invert_yaxis()
        self.plot.draw()


def fold_phase(t, period, t0):
    from ..timeseries.period import fold

    return fold(t, period, t0)


def fourier_edit():
    from ..timeseries import fourier

    return fourier


class LightCurvePage(QTabWidget):
    """Light curves & O-C: period search and O-C diagram as tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.period_page = PeriodPage(self)
        self.oc_page = OCPage(self)
        from .frequency_page import FrequencyPage
        from .varfind_page import VarFindPage

        self.frequency_page = FrequencyPage(self.period_page, self)
        self.varfind_page = VarFindPage(self)
        self.addTab(self.period_page, self.tr("Period search"))
        self.addTab(self.frequency_page, self.tr("Frequency analysis"))
        self.addTab(self.varfind_page, self.tr("Variable star search"))
        self.addTab(self.oc_page, self.tr("O-C diagram"))
