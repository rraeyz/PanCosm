"""Exposure time calculator: how long to expose for a wanted signal-to-noise, and when the star saturates."""

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QLabel, QVBoxLayout

from ..planning import exposure


class ExposureDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(self.tr("Exposure time"))
        saved = settings.get("exposure_calculator", {})
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.fields = {}
        for key, label, tip, value, lo, hi, dec in (
            (
                "magnitude",
                self.tr("Star magnitude"),
                self.tr("Brightness of the star in the filter used"),
                12.0,
                -2,
                25,
                2,
            ),
            (
                "zero_point",
                self.tr("Zero point (mag)"),
                self.tr(
                    "The magnitude that gives one electron per second with your telescope, camera and filter; "
                    "measure it once on a star of known magnitude (Photometry gives counts per second)"
                ),
                21.0,
                5,
                35,
                2,
            ),
            (
                "snr",
                self.tr("Wanted signal-to-noise"),
                self.tr("In one frame; 100 gives an error of about 0.01 mag"),
                100.0,
                1,
                100000,
                0,
            ),
            (
                "sky",
                self.tr("Sky (e⁻ / pixel / s)"),
                self.tr("Sky brightness measured on a frame of your site; less with the Moon down"),
                5.0,
                0,
                1e6,
                2,
            ),
            ("read_noise", self.tr("Read noise (e⁻)"), self.tr("From the camera's data sheet"), 10.0, 0, 1000, 1),
            (
                "dark",
                self.tr("Dark current (e⁻ / pixel / s)"),
                self.tr("At the camera's temperature; close to 0 for a cooled camera"),
                0.0,
                0,
                1000,
                3,
            ),
            (
                "aperture_px",
                self.tr("Aperture radius (px)"),
                self.tr("Radius used for the photometry, about 1 to 2 times the FWHM"),
                5.0,
                0.5,
                200,
                1,
            ),
            (
                "fwhm_px",
                self.tr("Star FWHM (px)"),
                self.tr("Size of the star images (seeing and focus): sets how fast the brightest pixel fills"),
                3.0,
                0.5,
                100,
                1,
            ),
            (
                "full_well",
                self.tr("Full well / saturation (e⁻)"),
                self.tr("Where the camera stops being linear (data sheet, or a series of flats)"),
                50000.0,
                100,
                1e7,
                0,
            ),
        ):
            box = QDoubleSpinBox(self)
            box.setRange(lo, hi)
            box.setDecimals(dec)
            box.setValue(float(saved.get(key, value)))
            box.setToolTip(tip)
            box.valueChanged.connect(self.update)
            self.fields[key] = box
            form.addRow(label, box)
        self.result = QLabel(self)
        self.result.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.Close, self)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(self.result)
        lay.addWidget(buttons)
        self.update()

    def values(self):
        return {k: box.value() for k, box in self.fields.items()}

    def update(self):
        v = self.values()
        self.settings.set("exposure_calculator", v)
        common = {k: v[k] for k in ("magnitude", "zero_point", "sky", "read_noise", "dark")}
        t = exposure.exposure_time(v["snr"], aperture_px=v["aperture_px"], **common)
        sat = exposure.saturation_seconds(
            v["full_well"], v["magnitude"], v["zero_point"], v["sky"], v["fwhm_px"], v["dark"]
        )
        text = self.tr("Exposure for S/N {snr:g}: {t:.1f} s").format(snr=v["snr"], t=t)
        text += "\n" + self.tr("The star's brightest pixel saturates after {s:.1f} s.").format(s=sat)
        if t > sat:
            text += "\n" + self.tr("Too long for one frame: take several shorter frames and add them, or defocus.")
        self.result.setText(text)
        return t
