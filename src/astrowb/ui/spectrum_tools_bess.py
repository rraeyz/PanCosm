"""Spectrum tools tab: the BeSS / ARAS export dialog."""

from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit


class BessDialog(QDialog):
    """The BeSS keywords the spectrum's header does not already give."""

    FIELDS = ("object", "observer", "date_obs", "exptime", "instrument", "site", "latitude", "longitude", "elevation")
    KEYS = ("OBJECT", "OBSERVER", "DATE-OBS", "EXPTIME", "INSTRUME", "SITENAME", "SITELAT", "SITELONG", "SITEELEV")

    def __init__(self, header=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Export for BeSS / ARAS"))
        form = QFormLayout(self)
        labels = (
            self.tr("Object (Simbad name)"),
            self.tr("Observer"),
            self.tr("Start of exposure (UTC)"),
            self.tr("Exposure (s)"),
            self.tr("Telescope + spectrograph + camera"),
            self.tr("Site"),
            self.tr("Latitude (°)"),
            self.tr("Longitude (°)"),
            self.tr("Elevation (m)"),
        )
        self.edits = {}
        for field, key, label in zip(self.FIELDS, self.KEYS, labels, strict=True):
            e = QLineEdit(str((header or {}).get(key, "")), self)
            self.edits[field] = e
            e.setToolTip(self.tr("A keyword BeSS requires; filled from the spectrum's header when it has it"))
            form.addRow(label, e)
        self.telluric = QCheckBox(self.tr("Telluric lines removed"), self)
        self.cosmic = QCheckBox(self.tr("Cosmic rays removed"), self)
        self.cosmic.setToolTip(self.tr("Tick if cosmic-ray hits were removed; written into the header for BeSS"))
        self.telluric.setToolTip(
            self.tr("Tick if the telluric (atmospheric) lines were divided out; written into the header for BeSS")
        )
        self.vhel = QLineEdit("0", self)
        self.vhel.setToolTip(
            self.tr(
                "The heliocentric velocity correction already applied to the wavelengths (0 if none); BeSS "
                "needs it to compare spectra"
            )
        )
        form.addRow(self.telluric)
        form.addRow(self.cosmic)
        form.addRow(self.tr("Heliocentric correction applied (km/s)"), self.vhel)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self):
        out = {k: e.text().strip() for k, e in self.edits.items()}
        for k in ("exptime", "latitude", "longitude", "elevation"):
            try:
                out[k] = float(out[k].replace(",", "."))
            except ValueError:
                out[k] = 0.0
        try:
            out["vhel"] = float(self.vhel.text().replace(",", "."))
        except ValueError:
            out["vhel"] = 0.0
        return out | {"telluric": self.telluric.isChecked(), "cosmic": self.cosmic.isChecked()}
