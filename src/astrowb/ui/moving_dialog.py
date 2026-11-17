"""Asteroid / comet astrometry: mark the object on the first and the last plate-solved frame, measure every
frame, write the MPC (ADES) report."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core import profiles
from .kit.table_view import DataTable
from .viewer import ImageViewer


class MovingObjectPage(QWidget):
    """The Astrometry window's page (UI-16.11): controls in the left column (the window shows them as stages),
    the frame and the positions on the right."""

    measure_requested = Signal(list, list, list)  # images, first_xy, last_xy
    solve_requested = Signal(str)  # one frame to plate-solve

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.images, self.first, self.last, self.positions = [], None, None, []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        split = QSplitter(Qt.Horizontal, self)
        lay.addWidget(split)
        self.left = QWidget(split)
        left = QVBoxLayout(self.left)
        right = QWidget(split)
        main = QVBoxLayout(right)
        self._controls(left)
        self.hint = QLabel(self.tr("Choose the frames (calibrated and plate-solved), in any order."), self)
        self.hint.setWordWrap(True)
        main.addWidget(self.hint)
        self.viewer = ImageViewer(self)
        self.viewer.clicked.connect(self._clicked)
        self.viewer.set_pick(True)  # clicks pick a point: a cross, not the hand; dragging still pans
        self.viewer.empty_hint = self.tr("The first frame appears here once the images are chosen")
        main.addWidget(self.viewer, 3)
        frame = DataTable(self)
        frame.prepare(["UTC", "RA (°)", "Dec (°)", self.tr("Residual (″)")])
        self.table = frame.table
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        main.addWidget(frame, 1)
        split.setStretchFactor(1, 1)
        from .stage_boxes import boxes_from_column

        starts = [("images", self.choose_button), ("solve", self.solve_info), ("find", self.find_info),
                  ("measure", self.measure_button), ("report", self.form_box)]  # fmt: skip
        self.stage_boxes = boxes_from_column(left, starts)

    def _controls(self, lay):
        self.choose_button = QPushButton(self.tr("Choose plate-solved frames…"), self)
        self.choose_button.clicked.connect(self._choose)
        self.choose_button.setToolTip(
            self.tr(
                "Calibrated frames with a plate solution (WCS) in the header, taken over an hour or more so"
                " the object moves"
            )
        )
        self.frames_info = QLabel(self)
        self.solve_info = QLabel(self.tr("Frames without a plate solution are solved first."), self)
        self.solve_button = QPushButton(self.tr("Solve the frames"), self)
        self.solve_button.setEnabled(False)
        self.solve_button.clicked.connect(self._solve)
        self.solve_button.setToolTip(
            self.tr("Plate-solves every chosen frame that has no solution yet (ASTAP or astrometry.net)")
        )
        self.find_info = QLabel(
            self.tr("Click the object on the first frame, then on the last frame; they are marked in the image."), self
        )
        self.measure_button = QPushButton(self.tr("Measure positions"), self)
        self.measure_button.setEnabled(False)
        self.measure_button.clicked.connect(
            lambda: self.measure_requested.emit(self.images, list(self.first), list(self.last))
        )
        self.measure_button.setToolTip(
            self.tr(
                "After clicking the object on the first and the last frame: its position is measured on "
                "every frame and fitted with a straight motion; residuals show bad points"
            )
        )
        for label in (self.frames_info, self.solve_info, self.find_info):
            label.setWordWrap(True)
        for w in (self.choose_button, self.frames_info, self.solve_info, self.solve_button, self.find_info,
                  self.measure_button):  # fmt: skip
            lay.addWidget(w)
        self.form_box = self._report_form(lay)

    def _report_form(self, lay):
        saved = profiles.section(self.settings, "observer")
        box = QWidget(self)
        form = QFormLayout(box)
        form.setContentsMargins(0, 0, 0, 0)
        self.designation = QLineEdit(self)
        self.designation.setPlaceholderText(self.tr("e.g. 2026 VA12, 433, or your own name for a new object"))
        self.designation.setToolTip(
            self.tr(
                "The object's designation as the Minor Planet Center knows it, or a temporary name of your "
                "own for a new object"
            )
        )
        self.code = QLineEdit(saved["mpc_code"], self)
        self.code.setPlaceholderText(self.tr("MPC observatory code, e.g. A84"))
        self.code.setToolTip(
            self.tr(
                "Your observatory's three-character code from the Minor Planet Center (ask them for one "
                "before the first report)"
            )
        )
        self.observers = QLineEdit(saved.get("observers", ""), self)
        self.observers.setPlaceholderText(self.tr("names, separated by commas"))
        self.observers.setToolTip(self.tr("Names of the observers, written into the report"))
        self.catalog = QLineEdit(saved.get("catalog", "Gaia3"), self)
        self.catalog.setToolTip(
            self.tr(
                "Star catalogue the plate solutions rest on (ADES astCat). Filled in from the frames when the solver "
                "recorded it: astrometry.net's 4100 indexes are Tycho-2 (Tyc2), 4200 are 2MASS, 5200 are Gaia DR2 "
                "(Gaia2); ASTAP's star databases come from Gaia (check which release yours is)"
            )
        )
        form.addRow(self.tr("Object"), self.designation)
        form.addRow(self.tr("Observatory code"), self.code)
        form.addRow(self.tr("Observers"), self.observers)
        form.addRow(self.tr("Catalogue"), self.catalog)
        self.format = QComboBox(self)
        self.format.addItem(self.tr("ADES PSV"), "ades")
        self.format.addItem(self.tr("MPC 80-column"), "mpc80")
        self.format.setToolTip(
            self.tr("File format of the report; the 80-column format is the older one for other tools")
        )
        form.addRow(self.tr("Format"), self.format)
        lay.addWidget(box)
        self.export_button = QPushButton(self.tr("Write MPC report (ADES)…"), self)
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(lambda: self.export())
        self.export_button.setToolTip(
            self.tr("Writes the positions in the MPC's ADES format, ready to send to the Minor Planet Center")
        )
        lay.addWidget(self.export_button)
        return box

    def _unsolved(self):
        from astropy.io import fits
        from astropy.wcs import WCS

        from ..io.fits import find_image_hdu

        def solved(p):
            with fits.open(p) as hdul:
                return WCS(hdul[find_image_hdu(hdul)].header).has_celestial

        return [p for p in self.images if not solved(p)]

    def _solve(self):
        for p in self._unsolved():
            self.solve_requested.emit(str(p))

    def solved(self, old, new):
        """A frame's plate-solved copy replaces it (the original is untouched)."""
        self.images = [str(new) if str(p) == str(old) else p for p in self.images]
        self._frames_changed()

    def _frames_changed(self):
        todo = len(self._unsolved())
        self.frames_info.setText(
            self.tr("{n} frames, {k} without a plate solution.").format(n=len(self.images), k=todo)
        )
        self.solve_button.setEnabled(todo > 0)

    def set_images(self, paths):
        from .. import timing
        from ..io.bayer import fits_paths
        from ..io.fits import read_image

        paths = fits_paths(paths)  # camera raw files and pictures get a FITS copy every tool can read

        self.images = timing.chronological(paths)
        self.first = self.last = None
        self.viewer.set_image(read_image(self.images[0])[0])
        self.hint.setText(self.tr("Click the object on the first frame."))
        self._frames_changed()

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

    def show_positions(self, rows, unsolved=()):
        self.positions = rows
        cats = {p.get("ast_cat") for p in rows} - {None}
        note = ""
        if len(cats) == 1 and (cat := cats.pop()) != self.catalog.text().strip():
            self.catalog.setText(cat)
            note = " " + self.tr("Catalogue set to {c}: the frames' plate solutions rest on it.").format(c=cat)
        elif len(cats) > 1:
            note = " " + self.tr("The frames were solved against different catalogues ({c}): solve them alike.").format(
                c=", ".join(sorted(cats))
            )
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
            + (
                " " + self.tr("{k} frames could not be plate-solved and were left out.").format(k=len(unsolved))
                if unsolved
                else ""
            )
            + note
        )
        self.export_button.setEnabled(bool(rows))

    def export(self, path=None):
        from ..photometry.moving import ades_psv
        from ..photometry.mpc80 import mpc80_text
        from .messages import translate

        old = self.format.currentData() == "mpc80"

        observers = [n.strip() for n in self.observers.text().split(",") if n.strip()]
        try:
            if old:
                text = mpc80_text(self.positions, self.designation.text().strip(), self.code.text())
            else:
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
        profiles.update(
            self.settings,
            "observer",
            mpc_code=self.code.text().strip().upper(),
            observers=self.observers.text(),
            catalog=self.catalog.text().strip(),
        )
        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self, self.tr("MPC report"), "obs80.txt" if old else "ades.psv", "MPC report (*.psv *.txt)"
            )
        if path:
            Path(path).write_text(text, encoding="utf-8")
            self.hint.setText(
                self.tr("Report written: {p}. Send it to the MPC (obs@minorplanetcenter.net or the web form).").format(
                    p=path
                )
            )
        return path


class MovingObjectDialog(QDialog):
    """The page in a dialog (the page itself is the Astrometry window's content)."""

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Asteroid and comet astrometry"))
        self.resize(1100, 760)
        self.page = MovingObjectPage(settings, self)
        QVBoxLayout(self).addWidget(self.page)
        self.measure_requested = self.page.measure_requested
        self.solve_requested = self.page.solve_requested

    def __getattr__(self, name):  # the page's widgets and methods, as when the dialog held them itself
        if name == "page":
            raise AttributeError(name)
        return getattr(self.page, name)
