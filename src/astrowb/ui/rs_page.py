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
SENTINEL2 = {"B02": "BLUE", "B03": "GREEN", "B04": "RED", "B08": "NIR", "B11": "SWIR"}


class RemoteSensingPage(QWidget):
    step_requested = Signal(str, dict, dict)  # step id, inputs, params

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("remotesensing")
        # display name -> (file, band): products are read from their file when shown, not all kept (a Sentinel-2 tile
        # with NDVI, two PCA components and classes kept 2 GB of products in the page)
        self.raster, self.products = None, {}
        split = QSplitter(Qt.Horizontal, self)
        self.viewer = ImageViewer(self)
        self.viewer.hovered.connect(self._hover)
        self.viewer.clicked.connect(self._clicked)
        self.viewer.set_pick(True)  # clicks pick a point: a cross, not the hand; dragging still pans
        split.addWidget(self.viewer)
        side = QWidget(self)
        lay = QVBoxLayout(side)
        lay.addWidget(_title(self.tr("Remote sensing"), self))
        from .workspaces import StepGuide

        self.guide = StepGuide(
            [
                (
                    self.tr("Open the image, or the band files of one scene"),
                    self.tr("Press Open image…; for Sentinel-2 or Landsat select all band files of the scene at once."),
                ),
                (
                    self.tr("Check which band is which"),
                    self.tr(
                        "Check the BLUE, GREEN, RED, NIR and SWIR band choices: they are filled from the file names "
                        "where possible."
                    ),
                ),
                (
                    self.tr("Compute an index (NDVI, NDWI…) or your own formula"),
                    self.tr("Choose an index or type a formula and press Compute."),
                ),
                (
                    self.tr("Optional: classify (k-means) or principal components"),
                    self.tr(
                        "Classify (k-means) groups similar pixels; Principal components finds the main patterns of "
                        "the bands."
                    ),
                ),
            ],
            self,
        )
        lay.addWidget(self.guide)
        open_button = QPushButton(self.tr("Open image (GeoTIFF, FITS, JPEG2000, NetCDF, HDF5)…"), self)
        open_button.clicked.connect(self._open)
        open_button.setToolTip(
            self.tr(
                "A satellite or aerial image with one or more bands; every band can be shown and used in the formulas."
                " Select several files at once for the bands of one scene that come one per file (Sentinel-2, Landsat)"
            )
        )
        lay.addWidget(open_button)
        self.info = QLabel(self.tr("No image"), self)
        self.info.setWordWrap(True)
        lay.addWidget(self.info)
        row = QHBoxLayout()
        row.addWidget(QLabel(self.tr("Show"), self))
        self.show_combo = QComboBox(self)
        self.show_combo.currentTextChanged.connect(self._show)
        self.show_combo.setToolTip(self.tr("Which band or result to show"))
        row.addWidget(self.show_combo, 1)
        lay.addLayout(row)
        lay.addWidget(QLabel(self.tr("Band roles (for the indices)"), self))
        grid = QGridLayout()
        self.roles = {}
        for i, role in enumerate(ROLES):
            grid.addWidget(QLabel(role, self), i // 3, 2 * (i % 3))
            combo = QComboBox(self)
            self.roles[role] = combo
            combo.setToolTip(self.tr("Which band of the image holds this colour; the indices (NDVI…) use these roles"))
            grid.addWidget(combo, i // 3, 2 * (i % 3) + 1)
        lay.addLayout(grid)
        row = QHBoxLayout()
        self.index = QComboBox(self)
        self.index.addItem(self.tr("Index…"))
        for name, (_, about) in analysis.INDICES.items():
            self.index.addItem(name)
            self.index.setItemData(self.index.count() - 1, about, Qt.ToolTipRole)
        self.index.activated.connect(self._preset)
        self.index.setToolTip(self.tr("A known index (NDVI, NDWI…) fills in its formula with the bands of the roles"))
        row.addWidget(self.index)
        self.expression = QLineEdit(self)
        self.expression.setPlaceholderText(self.tr("band math, e.g. (B4 - B3) / (B4 + B3)"))
        self.expression.setToolTip(self.tr("A formula of the bands B1, B2…: + − * / ** and numbers"))
        row.addWidget(self.expression, 1)
        lay.addLayout(row)
        self.compute_button = QPushButton(self.tr("Compute"), self)
        self.compute_button.clicked.connect(self._compute)
        self.compute_button.setToolTip(self.tr("Computes the formula for every pixel and shows the result"))
        lay.addWidget(self.compute_button)
        row = QHBoxLayout()
        self.k = QSpinBox(self)
        self.k.setRange(2, 30)
        self.k.setValue(5)
        self.k.setToolTip(self.tr("How many classes k-means divides the pixels into"))
        classify = QPushButton(self.tr("Classify (k-means)"), self)
        classify.clicked.connect(lambda: self._run("rs.classify", {}, {"k": self.k.value()}))
        classify.setToolTip(
            self.tr("Groups the pixels by their values in all bands into this many classes, without training data")
        )
        pca = QPushButton(self.tr("Principal components"), self)
        pca.clicked.connect(lambda: self._run("rs.pca", {}, {}))
        pca.setToolTip(
            self.tr(
                "New bands that are combinations of the old ones, the first holding the most variation; "
                "useful to see differences hidden in many bands"
            )
        )
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
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "",
            "",
            "Images (*.tif *.tiff *.TIF *.fits *.fit *.fts *.jp2 *.j2k *.nc *.nc4 *.h5 *.hdf5 *.he5 *.hdf)"
            ";;All files (*)",
        )
        if paths:
            self.open(";".join(paths))  # several: the bands of one scene (Sentinel-2, Landsat: a file per band)

    def open(self, path):
        from ..remotesensing import raster

        try:
            # whole when it fits the free memory (with room for the steps), else read by rows: band by band on screen
            self.raster = raster.load(path, factor=4.0)
        except Exception as e:  # not an image we can read: say so, keep the page usable
            self.status.setText(self.tr("Cannot open: {e}").format(e=translate(str(e))))
            return
        r = self.raster
        self.products = {}
        self.guide.reset()
        self.guide.set_state(0, "done")
        self.show_combo.blockSignals(True)
        self.show_combo.clear()
        self.show_combo.addItems(r.names)
        self.show_combo.blockSignals(False)
        for i, role in enumerate(ROLES):
            combo = self.roles[role]
            combo.clear()
            combo.addItems(r.names)
            default = {4: [0, 1, 2, 3, None], 5: [0, 1, 2, 3, 4]}.get(len(r.names), [None] * 5)[i]
            s2 = [n for n in r.names if SENTINEL2.get(n.upper()) == role]  # Sentinel-2 band files: their own roles
            default = r.names.index(s2[0]) if s2 else default
            # no band for this role: left empty (it showed the first band, and an index silently used the wrong one)
            combo.setCurrentIndex(-1 if default is None else default)
        crs = f"EPSG:{r.epsg}" if r.epsg else self.tr("no map projection")
        self.info.setText(
            self.tr("{name}: {n} bands, {nx} × {ny} px, {crs}").format(
                name=" + ".join(Path(p).name for p in str(path).split(";")),
                n=len(r.names),
                nx=r.shape[1],
                ny=r.shape[0],
                crs=crs,
            )
        )
        self._show(r.names[0])

    def _current(self):
        name = self.show_combo.currentText()
        if name in self.products:
            from ..remotesensing import raster

            path, i = self.products[name]
            return raster.read(path).band(i)
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

        n = raster.band_count(product["path"])
        stem = Path(product["path"]).stem
        for i in (1, 2):
            self.guide.set_state(i, "done")
        names = [stem] if n == 1 else [f"{stem}{i + 1}" for i in range(n)]  # one entry per component
        for i, name in enumerate(names):
            self.products[name] = (product["path"], i)
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
        spec = r.pixel(x, y).tolist() if hasattr(r, "pixel") else analysis.pixel_spectrum(r.bands, x, y)
        self.plot.figure.clear()
        ax = self.plot.figure.add_subplot()
        ax.plot(range(1, len(spec) + 1), spec, "o-")
        ax.set_xticks(range(1, len(spec) + 1), r.names if len(spec) <= 16 else None)
        ax.set_xlabel(self.tr("Band"))
        ax.set_ylabel(self.tr("Value at pixel {x:.0f}, {y:.0f}").format(x=x, y=y))
        self.plot.draw()
