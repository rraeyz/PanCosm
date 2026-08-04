"""Photometric coefficients: the night's extinction from the measured light curve, and transformation
coefficients from two images of a standard field."""

import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from .files import images_filter
from .workspaces import PlotCanvas

BANDS = ("B", "V", "R", "I", "SG", "SR", "SI")
FITS = "FITS (*.fits *.fit *.fts *.FITS *.FIT)"


class CoefficientsDialog(QDialog):
    transform_requested = Signal(str, str, dict)  # image A, image B, params

    def __init__(self, light_curve=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Photometric coefficients"))
        self.resize(820, 640)
        self.lc, self.paths, self.result = light_curve, ["", ""], None
        lay = QVBoxLayout(self)
        box = QGroupBox(self.tr("Extinction of the night"), self)
        bl = QVBoxLayout(box)
        self.ext_button = QPushButton(self.tr("From the comparison stars of the measured light curve"), self)
        self.ext_button.clicked.connect(self.compute_extinction)
        self.ext_button.setEnabled(bool(light_curve and light_curve.get("airmass")))
        if not self.ext_button.isEnabled():
            self.ext_button.setToolTip(
                self.tr("Measure a light curve whose frames give the sky position (airmass) first")
            )
        self.ext_result = QLabel(self)
        self.ext_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bl.addWidget(self.ext_button)
        bl.addWidget(self.ext_result)
        lay.addWidget(box)
        box = QGroupBox(self.tr("Transformation coefficients from a standard field"), self)
        g = QGridLayout(box)
        self.band = [QComboBox(self), QComboBox(self)]
        self.file_labels = [QLabel(self.tr("no image"), self), QLabel(self.tr("no image"), self)]
        for r, default in enumerate(("B", "V")):
            self.band[r].addItems(BANDS)
            self.band[r].setCurrentText(default)
            self.band[r].setToolTip(self.tr("Filter of this image of the standard field"))
            pick = QPushButton(self.tr("Plate-solved image…"), self)
            pick.clicked.connect(
                lambda _=False, i=r: self.set_image(i, QFileDialog.getOpenFileName(self, "", "", images_filter())[0])
            )
            g.addWidget(QLabel(self.tr("Filter {n}").format(n=r + 1), self), r, 0)
            g.addWidget(self.band[r], r, 1)
            g.addWidget(pick, r, 2)
            pick.setToolTip(
                self.tr(
                    "An image of a standard field (e.g. Landolt) through this filter, with a plate solution in "
                    "its header"
                )
            )
            g.addWidget(self.file_labels[r], r, 3)
        self.tr_button = QPushButton(self.tr("Compute (catalogue magnitudes from VizieR)"), self)
        self.tr_button.setEnabled(False)
        self.tr_button.clicked.connect(self._transform)
        self.tr_button.setToolTip(
            self.tr(
                "Measures the stars of both images, looks up their catalogue magnitudes and fits the colour"
                " terms of the transformation to the standard system (needs the internet)"
            )
        )
        g.addWidget(self.tr_button, 2, 0, 1, 4)
        self.tr_result = QLabel(self)
        self.tr_result.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.tr_result.setWordWrap(True)
        g.addWidget(self.tr_result, 3, 0, 1, 4)
        lay.addWidget(box)
        self.plot = PlotCanvas(self)
        lay.addWidget(self.plot, 1)

    def compute_extinction(self):
        from ..photometry.coefficients import extinction

        flux = np.asarray(self.lc["comp_flux"], float)  # the target may vary: comparison stars only
        try:
            k = extinction(self.lc["airmass"], flux)
        except ValueError as e:
            from .messages import translate

            self.ext_result.setText(translate(str(e)))
            return None
        self.ext_result.setText(
            self.tr("k = {k:.3f} ± {e:.3f} mag per airmass ({n} measurements, rms {r:.3f} mag)").format(
                k=k["k"], e=k["k_err"], n=k["n"], r=k["rms"]
            )
        )
        x = np.asarray(self.lc["airmass"], float)
        m = -2.5 * np.log10(np.clip(flux, 1e-9, None))
        self.plot.figure.clear()
        ax = self.plot.figure.subplots()
        for j in range(m.shape[1]):
            ax.plot(x, m[:, j] - np.nanmean(m[:, j]), ".", ms=3)
        xs = np.linspace(x.min(), x.max(), 2)
        ax.plot(xs, k["k"] * (xs - x.mean()), "k-", lw=1)
        ax.invert_yaxis()
        ax.set_xlabel(self.tr("Airmass"))
        ax.set_ylabel(self.tr("Instrumental magnitude − mean"))
        self.plot.draw()
        return k

    def set_image(self, i, path):
        from pathlib import Path

        if path:
            from ..io.bayer import fits_copy

            path = str(fits_copy(path))  # a camera raw file or picture: its FITS copy
            self.paths[i] = path
            self.file_labels[i].setText(Path(path).name)
        self.tr_button.setEnabled(all(self.paths))

    def _transform(self):
        self.result = None
        self.tr_result.setText(self.tr("Measuring and querying the catalogue…"))
        params = {"band_a": self.band[0].currentText(), "band_b": self.band[1].currentText()}
        self.transform_requested.emit(self.paths[0], self.paths[1], params)

    def show_transformation(self, out):
        self.result = out
        c = out["transformation"]
        a, b = self.band[0].currentText(), self.band[1].currentText()
        lines = [self.tr("{n} standard stars").format(n=c["n"])]
        for key, label in (
            (f"t{a}{b}".lower(), f"T{a.lower()}{b.lower()}"),
            (f"t{b}".lower(), f"T{b.lower()}"),
            (f"t{a}".lower(), f"T{a.lower()}"),
        ):
            v = c[key]
            lines.append(
                self.tr("{name} = {v:.4f} ± {e:.4f} (zero point {z:.3f}, rms {r:.3f}, {u} stars)").format(
                    name=label, v=v["value"], e=v["error"], z=v["zero_point"], r=v["rms"], u=v["used"]
                )
            )
        self.tr_result.setText("\n".join(lines))
        s = out["stars"]
        ca, cb, ia, ib = (np.asarray(s[k], float) for k in ("cat_a", "cat_b", "inst_a", "inst_b"))
        t = c[f"t{a}{b}".lower()]
        self.plot.figure.clear()
        ax = self.plot.figure.subplots()
        ax.plot(ia - ib, ca - cb, "o", ms=4)
        xs = np.linspace(np.nanmin(ia - ib), np.nanmax(ia - ib), 2)
        ax.plot(xs, t["value"] * xs + t["zero_point"], "k-", lw=1)
        ax.set_xlabel(f"{a.lower()} − {b.lower()}")
        ax.set_ylabel(f"{a} − {b}")
        self.plot.draw()
