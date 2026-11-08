"""The Images page: viewer, inspection tools and processing of single images."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .messages import translate
from .undo import Undoable
from .viewer import ImageViewer
from .widgets import PlotCanvas


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
        self.viewer.empty_hint = self.tr("No image yet: File → Open…, or drop image files here")
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
        self.header_table.cellDoubleClicked.connect(lambda _row, _col: self.edit_keyword_dialog())
        self.header_table.setToolTip(
            self.tr("Double-click a keyword to change it; drag a column's edge to widen it; right-click to copy")
        )
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
