"""Time and coordinate converter (plans/architecture.md ARC-15 item 3): a target and the site of the profile, a
column of times in one standard → the same times in every standard, with altitude, azimuth, hour angle and
airmass (core/units.convert_times). Pasting a whole column converts it; Copy puts the table on the clipboard."""

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..core import profiles, units
from .messages import translate

COLUMNS = (*units.STANDARDS, "alt", "az", "ha", "airmass")


class ConverterDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle(self.tr("Time converter"))
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.target = QLineEdit(self)
        self.target.setPlaceholderText(self.tr("name (SIMBAD) or coordinates, e.g. 02:04:10.3 +46:41:16"))
        self.target.setToolTip(self.tr("Heliocentric and barycentric times depend on the direction of the star"))
        form.addRow(self.tr("Target"), self.target)
        site = profiles.section(settings, "site")
        self.site = QLabel(
            self.tr("{name} {lat:.4f}°, {lon:.4f}°, {h:.0f} m (from the profile; Planning changes it)").format(
                name=site["name"], lat=site["lat"], lon=site["lon"], h=site["height"]
            ),
            self,
        )
        form.addRow(self.tr("Site"), self.site)
        self.standard = QComboBox(self)
        self.standard.addItems(units.STANDARDS)
        self.standard.setToolTip(
            self.tr("What the times below are. Old literature gives HJD without its time scale: try HJD_UTC")
        )
        form.addRow(self.tr("Times given as"), self.standard)
        self.times = QPlainTextEdit(self)
        self.times.setPlaceholderText(self.tr("one time per line (Julian dates; MJD for MJD_UTC)"))
        self.times.setMaximumHeight(110)
        form.addRow(self.tr("Times"), self.times)
        lay.addLayout(form)
        buttons = QHBoxLayout()
        self.convert_button = QPushButton(self.tr("Convert"), self)
        self.convert_button.clicked.connect(self.convert)
        self.copy_button = QPushButton(self.tr("Copy"), self)
        self.copy_button.clicked.connect(lambda: QApplication.clipboard().setText(self.text()))
        buttons.addWidget(self.convert_button)
        buttons.addWidget(self.copy_button)
        buttons.addStretch(1)
        lay.addLayout(buttons)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.table = QTableWidget(0, len(COLUMNS), self)
        self.table.setHorizontalHeaderLabels(COLUMNS)
        lay.addWidget(self.table, 1)
        self.resize(1000, 520)
        self.result = None

    def _target(self):
        from ..planning.targets import Resolver
        from ..settings import config_dir

        t = Resolver(config_dir() / "targets.json").resolve(self.target.text())
        return t.coord

    def convert(self):
        from astropy import units as u
        from astropy.coordinates import EarthLocation

        try:
            values = [float(v.replace(",", ".")) for v in self.times.toPlainText().split() if v.strip()]
            if not values:
                self.status.setText(self.tr("Give at least one time."))
                return None
            site = profiles.section(self.settings, "site")
            where = EarthLocation.from_geodetic(site["lon"] * u.deg, site["lat"] * u.deg, site["height"] * u.m)
            self.result = units.convert_times(values, self.standard.currentText(), self._target(), where)
        except (ValueError, LookupError, OSError) as e:
            self.status.setText(translate(str(e)))
            return None
        n = len(values)
        self.status.setText(
            self.tr("{n} times converted.").format(n=n)
            + ("" if "alt" in self.result else " " + self.tr("Altitudes are left out for more than 2000 times."))
            + self._scale_doubt()
        )
        shown = min(n, 2000)
        self.table.setRowCount(shown)
        for col, key in enumerate(COLUMNS):
            column = self.result.get(key)
            for row in range(shown if column is not None else 0):
                v = float(column[row])
                text = f"{v:.6f}" if key in units.STANDARDS else f"{v:.3f}"
                self.table.setItem(row, col, QTableWidgetItem(text))
        return self.result

    def _scale_doubt(self):
        """Old literature gives HJD without saying UTC or TT (ARC-15 item 4): how far apart the two readings are."""
        if not self.standard.currentText().startswith("HJD"):
            return ""
        apart = float(np.max(np.abs(self.result["JD_TT"] - self.result["JD_UTC"]))) * 86400
        return " " + self.tr(
            "If the source did not say whether its HJD is in UTC or TT, the times may be off by up to {s:.1f} s "
            "(TT − UTC on those dates)."
        ).format(s=apart)

    def text(self):
        """The whole result, tab-separated with a header line (every row, also beyond the 2000 shown)."""
        if self.result is None:
            return ""
        keys = [k for k in COLUMNS if k in self.result]
        rows = np.column_stack([self.result[k] for k in keys])
        return "\n".join(["\t".join(keys), *("\t".join(f"{v:.8f}" for v in r) for r in rows)])


def converter_button(page):
    """Planning's "Time converter…" button (texts in the Planning window's translation context)."""
    button = QPushButton(QCoreApplication.translate("PlanPage", "Time converter…"), page)
    button.setToolTip(
        QCoreApplication.translate(
            "PlanPage", "JD, HJD and BJD in UTC, TT or TDB, altitude and airmass for a target and the site"
        )
    )
    button.clicked.connect(page.converter_dialog)
    return button
