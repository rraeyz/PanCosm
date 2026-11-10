"""Measure the camera… (plans/calibration.md CAL-9): two flats and two biases give the gain and the read noise
(calibration/detector.py), which go into the camera profile that cosmic-ray cleaning and photometry read."""

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

from ..core import profiles
from .kit.dialogs import Dialog


class CameraDialog(Dialog):
    def __init__(self, settings, parent=None):
        super().__init__(self.tr("Measure the camera"), parent, settings, "camera_measure")
        self.settings = settings
        self.result = None
        form = QFormLayout()
        self.paths = {}
        for key, label in (("flat1", self.tr("Flat 1")), ("flat2", self.tr("Flat 2")), ("bias1", self.tr("Bias 1")),
                           ("bias2", self.tr("Bias 2"))):  # fmt: skip
            row = QWidget(self)
            lay = QHBoxLayout(row)
            lay.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit(row)
            browse = QPushButton(self.tr("Browse…"), row)
            browse.clicked.connect(lambda _on=False, e=edit: self._browse(e))
            lay.addWidget(edit, 1)
            lay.addWidget(browse)
            self.paths[key] = edit
            form.addRow(label, row)
        text = self.tr(
            "Two flats of the same level (a third to two thirds of full well) and two biases, all of the same "
            "binning; the frames as the camera gave them, not calibrated."
        )
        note = QLabel(text, self)
        note.setWordWrap(True)
        self.body.addWidget(note)
        self.body.addLayout(form)
        self.measure_button = QPushButton(self.tr("Measure"), self)
        self.measure_button.clicked.connect(self.measure)
        self.answer = QLabel(self)
        self.answer.setWordWrap(True)
        self.save_button = QPushButton(self.tr("Save to the camera profile"), self)
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save)
        for w in (self.measure_button, self.answer, self.save_button):
            self.body.addWidget(w)

    def _browse(self, edit):
        path = QFileDialog.getOpenFileName(self, self.tr("Choose a frame"), "", "FITS (*.fits *.fit *.fts *.fz)")[0]
        if path:
            edit.setText(path)

    def measure(self):
        from ..calibration.detector import gain_read_noise
        from ..calibration.masters import load
        from .messages import translate

        try:
            frames = [load(Path(self.paths[k].text().strip()))[0] for k in ("flat1", "flat2", "bias1", "bias2")]
            self.result = gain_read_noise(*frames)
        except (OSError, ValueError) as e:
            self.answer.setText(translate(e))
            self.save_button.setEnabled(False)
            return None
        r = self.result
        self.answer.setText(
            self.tr("Gain {g:.3f} ± {ge:.3f} e⁻/ADU, read noise {rn:.2f} ± {rne:.2f} e⁻ (from {n} boxes).").format(
                g=r["gain"], ge=r["gain_err"], rn=r["read_noise"], rne=r["read_noise_err"], n=r["boxes"]
            )
        )
        self.save_button.setEnabled(True)
        return r

    def save(self):
        if self.result:
            profiles.update(self.settings, "camera", gain=round(self.result["gain"], 4),
                            read_noise=round(self.result["read_noise"], 3))  # fmt: skip
            self.answer.setText(self.answer.text() + " " + self.tr("Saved to the camera profile."))
