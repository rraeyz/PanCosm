"""The fields an AAVSO Extended report needs that the light curve does not know; the observer code comes from the
profile (ARC-16) and goes back into it."""

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit

from ..core import profiles
from ..settings import Settings


class AavsoDialog(QDialog):
    """The fields an AAVSO Extended report needs that the light curve does not know."""

    FILTERS = ("V", "B", "R", "I", "CV", "CR", "TG", "TB", "TR", "SG", "SR", "SI", "U")

    def __init__(self, n_comps, parent=None, settings=None):
        super().__init__(parent)
        self.settings = settings or Settings()
        self.setWindowTitle(self.tr("AAVSO report"))
        form = QFormLayout(self)
        self.star, self.obscode, self.mags = QLineEdit(self), QLineEdit(self), QLineEdit(self)
        self.chart, self.notes = QLineEdit(self), QLineEdit(self)
        self.filter = QComboBox(self)
        self.filter.addItems(self.FILTERS)
        self.mags.setPlaceholderText(self.tr("{n} values, e.g. 11.20, 11.85").format(n=n_comps))
        self.notes.setToolTip(self.tr("Anything a reader of the data should know (clouds, Moon, instrument)"))
        self.chart.setToolTip(self.tr("The identifier of the AAVSO chart (VSP) the comparison magnitudes come from"))
        self.filter.setToolTip(self.tr("Filter of the images, as AAVSO names it (CV: unfiltered, reduced to V)"))
        self.obscode.setToolTip(self.tr("Your AAVSO observer code"))
        self.star.setToolTip(self.tr("The variable's name as in AAVSO's VSX, e.g. AI DRA"))
        self.mags.setToolTip(
            self.tr("The comparison stars' magnitudes from the AAVSO chart (VSP), in the order the stars were marked")
        )
        form.addRow(self.tr("Star name (AAVSO VSX)"), self.star)
        self.obscode.setText(profiles.section(self.settings, "observer")["aavso_code"])
        form.addRow(self.tr("Observer code"), self.obscode)
        form.addRow(self.tr("Filter"), self.filter)
        form.addRow(self.tr("Catalogue magnitudes of the comparison stars"), self.mags)
        self.check = QLineEdit(self)
        self.check.setPlaceholderText(self.tr("label on the chart, e.g. 123"))
        self.check.setToolTip(
            self.tr(
                "The first check star's label on the chart; its magnitude goes into the report as a test of"
                " the comparison stars"
            )
        )
        form.addRow(self.tr("Check star (KNAME)"), self.check)
        form.addRow(self.tr("Chart ID"), self.chart)
        form.addRow(self.tr("Notes"), self.notes)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def accept(self):
        profiles.update(self.settings, "observer", aavso_code=self.obscode.text().strip().upper())
        super().accept()

    def values(self):
        mags = [float(v) for v in self.mags.text().replace(";", ",").split(",") if v.strip()]
        return {
            "star_name": self.star.text().strip(),
            "obscode": self.obscode.text().strip().upper(),
            "filt": self.filter.currentText(),
            "comp_mags": mags,
            "chart": self.chart.text().strip() or "na",
            "notes": self.notes.text().strip().replace(",", ";") or "na",
        }
