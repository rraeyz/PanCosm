"""Remote sensing: open a GeoTIFF (or FITS), look at bands, compute indices / band math, classify,
PCA; every product is a georeferenced GeoTIFF written next to the input."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..remotesensing import analysis
from .messages import translate
from .viewer import ImageViewer
from .workspaces import PlotCanvas, _title

ROLES = ("BLUE", "GREEN", "RED", "NIR", "SWIR")


class RemoteSensingPage(QWidget):
    step_requested = Signal(str, dict, dict)  # step id, inputs, params

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("remotesensing")
        self.raster, self.products = None, {}  # display name -> Raster
        split = QSplitter(Qt.Horizontal, self)
        self.viewer = ImageViewer(self)
        self.viewer.hovered.connect(self._hover)
        self.viewer.clicked.connect(self._clicked)
        self.viewer.set_pick(True)  # clicks pick a point: a cross, not the hand; dragging still pans
        split.addWidget(self.viewer)
        side = QWidget(self)
        lay = QVBoxLayout(side)
        lay.addWidget(_title(self.tr("Remote sensing"), self))
        open_button = QPushButton(self.tr("Open image (GeoTIFF, FITS, JPEG2000, NetCDF, HDF5)…"), self)
        open_button.clicked.connect(self._open)
        lay.addWidget(open_button)
        self.info = QLabel(self.tr("No image"), self)
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Show"), self))
        self.show_combo = QComboBox(self)
        self.show_combo.currentTextChanged.connect(self._show)
        row.addWidget(self.show_combo, 1)
        lay.addLayout(row)
        lay.addWidget(QLabel(self.tr("Band roles (for the indices)"), self))
        grid = QGridLayout()
        self.roles = {}
        for i, role in enumerate(ROLES):
            grid.addWidget(QLabel(role, self), i // 3, 2 * (i % 3))
            combo = QComboBox(self)
            self.roles[role] = combo
            grid.addWidget(combo, i // 3, 2 * (i % 3) + 1)
        lay.addLayout(grid)
        row = QHBoxLayout()
        self.index = QComboBox(self)
        self.index.addItem(self.tr("Index…"))
        for name, (_, about) in analysis.INDICES.items():
            self.index.addItem(name)
            self.index.setItemData(self.index.count() - 1, about, Qt.ToolTipRole)
        self.index.activated.connect(self._preset)
        row.addWidget(self.index)
        self.expression = QLineEdit(self)
        self.expression.setPlaceholderText(self.tr("band math, e.g. (B4 - B3) / (B4 + B3)"))
        row.addWidget(self.expression, 1)
        lay.addLayout(row)
        self.compute_button = QPushButton(self.tr("Compute"), self)
        self.compute_button.clicked.connect(self._compute)
        lay.addWidget(self.compute_button)
        row = QHBoxLayout()
        self.k = QSpinBox(self)
        self.k.setRange(2, 30)
        self.k.setValue(5)
        classify = QPushButton(self.tr("Classify (k-means)"), self)
        classify.clicked.connect(lambda: self._run("rs.classify", {}, {"k": self.k.value()}))
        pca = QPushButton(self.tr("Principal components"), self)
        pca.clicked.connect(lambda: self._run("rs.pca", {}, {}))
        row.addWidget(QLabel(self.tr("classes"), self))
        row.addWidget(self.k)
        row.addWidget(classify)
        row.addWidget(pca)
        lay.addLayout(row)
        self.readout = QLabel(self)
        self.readout.setWordWrap(True)
        self.readout.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.readout)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.status)
        self.plot = PlotCanvas(self)
        lay.addWidget(self.plot, 1)
        split.addWidget(side)
        split.setSizes([800, 420])
        QVBoxLayout(self).addWidget(split)

    # --- data ---------------------------------------------------------------
    def _open(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "",
            "",
            "Images (*.tif *.tiff *.TIF *.fits *.fit *.fts *.jp2 *.j2k *.nc *.nc4 *.h5 *.hdf5 *.he5 *.hdf)"
            ";;All files (*)",
        )
        if path:
            self.open(path)

    def open(self, path):
        from ..remotesensing import raster

        try:
            self.raster = raster.read(path)
        except Exception as e:  # not an image we can read: say so, keep the page usable
            self.status.setText(self.tr("Cannot open: {e}").format(e=translate(str(e))))
            return
        r = self.raster
        self.products = {}
        self.show_combo.blockSignals(True)
        self.show_combo.clear()
        self.show_combo.addItems(r.names)
        self.show_combo.blockSignals(False)
        for i, role in enumerate(ROLES):
            combo = self.roles[role]
            combo.clear()
            combo.addItems(r.names)
            default = {4: [0, 1, 2, 3, None], 5: [0, 1, 2, 3, 4]}.get(len(r.names), [None] * 5)[i]
            if default is not None:
                combo.setCurrentIndex(default)
        crs = f"EPSG:{r.epsg}" if r.epsg else self.tr("no map projection")
        self.info.setText(
            self.tr("{name}: {n} bands, {nx} × {ny} px, {crs}").format(
                name=Path(path).name, n=len(r.names), nx=r.shape[1], ny=r.shape[0], crs=crs
            )
        )
        self._show(r.names[0])

    def _current(self):
        name = self.show_combo.currentText()
        if name in self.products:
            return self.products[name].band(0)
        if self.raster and name in self.raster.names:
            return self.raster.band(self.raster.names.index(name))
        return None

    def _show(self, name):
        data = self._current()
        if data is None:
            return
        filled = np.nan_to_num(data, nan=float(np.nanmin(data)) if np.isfinite(data).any() else 0.0)
        self.viewer.set_image(np.flipud(filled))  # the viewer puts row 0 at the bottom (FITS); maps have north up
        st = analysis.statistics(data)
        if st["n"]:
            self.status.setText(
                self.tr(
                    "{name}: min {min:.4g}, median {median:.4g}, max {max:.4g}, mean {mean:.4g} ± {std:.4g}"
                ).format(name=name, **st)
            )

    def _preset(self, i):
        if i == 0:
            return
        name = self.index.itemText(i)
        roles = {role: c.currentText() for role, c in self.roles.items() if c.currentText()}
        self.expression.setText(analysis.index_expression(name, roles))
        self._product_name = name

    # --- products -----------------------------------------------------------
    def _compute(self):
        expr = self.expression.text().strip()
        if not expr:
            self.status.setText(self.tr("Type an expression or choose an index."))
            return
        try:  # check it here so typing errors are reported at once
            analysis.evaluate(expr, {n: np.zeros(1) for n in self.raster.names})
        except analysis.ExpressionError as e:
            self.status.setText(translate(str(e)))
            return
        name = getattr(self, "_product_name", None)
        if name and analysis.index_expression(name, {r: c.currentText() for r, c in self.roles.items()}) != expr:
            name = None
        self._run("rs.expression", {"expression": expr, "name": name or "expr"}, {})

    def _run(self, step_id, inputs, params):
        if self.raster is None:
            self.status.setText(self.tr("Open an image first."))
            return
        self.status.setText(self.tr("Working…"))
        self.step_requested.emit(step_id, {"raster": self.raster.source} | inputs, params)

    def show_product(self, product):
        from ..remotesensing import raster

        r = raster.read(product["path"])
        stem = Path(product["path"]).stem
        if len(r.names) == 1:
            self.products[stem] = r
            names = [stem]
        else:  # one entry per component
            names = []
            for i in range(len(r.names)):
                sub = raster.Raster(r.bands[i : i + 1], [f"{stem}{i + 1}"], r.transform, r.epsg, r.nodata, r.tags)
                self.products[f"{stem}{i + 1}"] = sub
                names.append(f"{stem}{i + 1}")
        for n in names:
            if self.show_combo.findText(n) < 0:
                self.show_combo.addItem(n)
        self.show_combo.setCurrentText(names[0])
        self._show(names[0])
        extra = ""
        if product.get("explained"):
            extra = " " + self.tr("Explained variance: {v}").format(
                v=", ".join(f"{100 * v:.1f} %" for v in product["explained"])
            )
        self.status.setText(self.status.text() + "\n" + self.tr("Saved: {p}").format(p=product["path"]) + extra)

    # --- pointer ------------------------------------------------------------
    def _pixel(self, col_view, row_view):
        """Image (column, row from the top) of a viewer position."""
        return int(np.floor(col_view)), self.raster.shape[0] - 1 - int(np.floor(row_view))

    def _hover(self, x, y, value):
        r = self.raster
        if r is None:
            return
        col, row = self._pixel(x - 1, y - 1)  # hovered gives 1-based FITS pixels
        text = self.tr("pixel {x:.0f}, {y:.0f}: {v:.5g}").format(x=col, y=row, v=value)
        xy = r.map_xy(col + 0.5, row + 0.5)
        if xy:
            text += f"   X {xy[0]:.2f}  Y {xy[1]:.2f}"
            try:
                ll = r.lonlat(col + 0.5, row + 0.5)
            except Exception:  # unknown or unsupported CRS: map coordinates only
                ll = None
            if ll:
                text += f"   {ll[1]:.6f}°, {ll[0]:.6f}°"
        self.readout.setText(text)

    def _clicked(self, x, y):
        r = self.raster
        if r is None:
            return
        x, y = self._pixel(x + 0.5, y + 0.5)  # clicked gives 0-based pixel centres
        if not (0 <= y < r.shape[0] and 0 <= x < r.shape[1]):
            return
        spec = analysis.pixel_spectrum(r.bands, x, y)
        self.plot.figure.clear()
        ax = self.plot.figure.add_subplot()
        ax.plot(range(1, len(spec) + 1), spec, "o-")
        ax.set_xticks(range(1, len(spec) + 1), r.names if len(spec) <= 16 else None)
        ax.set_xlabel(self.tr("Band"))
        ax.set_ylabel(self.tr("Value at pixel {x:.0f}, {y:.0f}").format(x=x, y=y))
        self.plot.draw()
