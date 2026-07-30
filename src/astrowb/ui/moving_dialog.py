"""Asteroid / comet astrometry: mark the object on the first and the last plate-solved frame, measure every
frame, write the MPC (ADES) report."""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from .viewer import ImageViewer


class MovingObjectDialog(QDialog):
    measure_requested = Signal(list, list, list)  # images, first_xy, last_xy

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(self.tr("Asteroid and comet astrometry"))
        self.resize(1100, 760)
        self.images, self.first, self.last, self.positions = [], None, None, []
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        choose = QPushButton(self.tr("Choose plate-solved frames…"), self)
        choose.clicked.connect(self._choose)
        self.measure_button = QPushButton(self.tr("Measure positions"), self)
        self.measure_button.setEnabled(False)
        self.measure_button.clicked.connect(
            lambda: self.measure_requested.emit(self.images, list(self.first), list(self.last))
        )
        row.addWidget(choose)
        row.addWidget(self.measure_button)
        lay.addLayout(row)
        self.hint = QLabel(self.tr("Choose the frames (calibrated and plate-solved), in any order."), self)
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)
        self.viewer = ImageViewer(self)
        self.viewer.clicked.connect(self._clicked)
        lay.addWidget(self.viewer, 3)
        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(["UTC", "RA (°)", "Dec (°)", self.tr("Residual (″)")])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        lay.addWidget(self.table, 1)
        saved = settings.get("mpc", {})
        form = QFormLayout()
        self.designation = QLineEdit(self)
        self.designation.setPlaceholderText(self.tr("e.g. 2026 VA12, 433, or your own name for a new object"))
        self.code = QLineEdit(saved.get("code", ""), self)
        self.code.setPlaceholderText(self.tr("MPC observatory code, e.g. A84"))
        self.observers = QLineEdit(saved.get("observers", ""), self)
        self.observers.setPlaceholderText(self.tr("names, separated by commas"))
        self.catalog = QLineEdit(saved.get("catalog", "Gaia3"), self)
        self.catalog.setToolTip(self.tr("Star catalogue of the plate solutions (ASTAP and astrometry.net: Gaia)"))
        form.addRow(self.tr("Object"), self.designation)
        form.addRow(self.tr("Observatory code"), self.code)
        form.addRow(self.tr("Observers"), self.observers)
        form.addRow(self.tr("Catalogue"), self.catalog)
        lay.addLayout(form)
        self.export_button = QPushButton(self.tr("Write MPC report (ADES)…"), self)
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(lambda: self.export())
        lay.addWidget(self.export_button)

    def set_images(self, paths):
        from .. import timing
        from ..io.bayer import fits_paths
        from ..io.fits import read_image

        paths = fits_paths(paths)  # camera raw files and pictures get a FITS copy every tool can read

        self.images = timing.chronological(paths)
        self.first = self.last = None
        self.viewer.set_image(read_image(self.images[0])[0])
        self.hint.setText(self.tr("Click the object on the first frame."))

    def _choose(self):
        from .files import images_filter

        paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Choose frames"), "", images_filter())
        if len(paths) >= 2:
            self.set_images(paths)

    def _clicked(self, x, y):
        from ..io.fits import read_image

        if not self.images:
            return
        if self.first is None:
            self.first = (x, y)
            self.viewer.set_image(read_image(self.images[-1])[0])
            self.viewer.set_markers([(*self.first, 6, "lime", "1")])
            self.hint.setText(self.tr("Now click the object on the last frame (the first position is marked)."))
        else:
            self.last = (x, y)
            self.viewer.set_markers([(*self.first, 6, "lime", "1"), (x, y, 6, "red", "2")])
            self.hint.setText(self.tr("Press Measure positions."))
            self.measure_button.setEnabled(True)

    def show_positions(self, rows):
        self.positions = rows
        self.table.setRowCount(len(rows))
        for r, p in enumerate(rows):
            resid = "—" if p["resid"] is None else f"{p['resid']:.2f}"
            for c, text in enumerate((p["time"][:22], f"{p['ra']:.6f}", f"{p['dec']:+.6f}", resid)):
                self.table.setItem(r, c, QTableWidgetItem(text))
        worst = max((p["resid"] or 0) for p in rows) if rows else 0
        self.hint.setText(
            self.tr("{n} positions. Largest residual {w:.2f}″ (more than ~1″: check that frame).").format(
                n=len(rows), w=worst
            )
        )
        self.export_button.setEnabled(bool(rows))

    def export(self, path=None):
        from ..photometry.moving import ades_psv
        from .messages import translate

        observers = [n.strip() for n in self.observers.text().split(",") if n.strip()]
        try:
            text = ades_psv(
                self.positions,
                self.designation.text().strip(),
                self.code.text().strip().upper(),
                observers,
                ast_cat=self.catalog.text().strip() or "Gaia3",
            )
        except ValueError as e:
            self.hint.setText(translate(str(e)))
            return None
        self.settings.set(
            "mpc",
            {
                "code": self.code.text().strip().upper(),
                "observers": self.observers.text(),
                "catalog": self.catalog.text().strip(),
            },
        )
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, self.tr("MPC report"), "ades.psv", "ADES PSV (*.psv *.txt)")
        if path:
            Path(path).write_text(text, encoding="utf-8")
            self.hint.setText(
                self.tr("Report written: {p}. Send it to the MPC (obs@minorplanetcenter.net or the web form).").format(
                    p=path
                )
            )
        return path
