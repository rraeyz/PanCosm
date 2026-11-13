"""The fields an AAVSO Extended report needs that the light curve does not know; the observer code comes from the
profile (ARC-16) and goes back into it."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QPushButton

from ..core import profiles
from ..settings import Settings


class AavsoDialog(QDialog):
    """The fields an AAVSO Extended report needs that the light curve does not know."""

    FILTERS = profiles.AAVSO_BANDS

    def __init__(self, n_comps, parent=None, settings=None, sequence=None):
        """sequence: filt -> (chart id, [{label, mag, err} or None per comparison star], check star's or None), the
        page's look-up of the AAVSO chart (from_sequence); None: no button."""
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
        self.sequence_note = QLabel(self)
        self.sequence_note.setWordWrap(True)
        if sequence:
            button = self.sequence_button = QPushButton(self.tr("Take them from the AAVSO chart (VSP)"), self)
            button.setToolTip(
                self.tr(
                    "The field's AAVSO comparison sequence: each marked star's magnitude in this filter, its label"
                    " and the chart ID (needs the plate solution and, once, the internet)"
                )
            )
            button.clicked.connect(lambda: self._take_sequence(sequence))
            form.addRow("", button)
        form.addRow("", self.sequence_note)
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

    def _take_sequence(self, sequence):
        try:
            chart, comps, check = sequence(self.filter.currentText())
        except (ValueError, LookupError, ConnectionError, OSError) as e:
            from .messages import translate

            self.sequence_note.setText(translate(e))
            return
        missing = [str(i + 1) for i, c in enumerate(comps) if c is None]
        if not missing:
            self.mags.setText(", ".join(f"{c['mag']:.3f}" for c in comps))
        self.chart.setText(chart)
        if check:
            self.check.setText(check["label"])
        labels = ", ".join(f"C{i + 1} = {c['label']}" for i, c in enumerate(comps) if c)
        self.sequence_note.setText(
            self.tr("Chart {chart}: {labels}.").format(chart=chart, labels=labels or "—")
            + (
                " "
                + self.tr("Not in the sequence: C{stars}; choose sequence stars or type the magnitudes.").format(
                    stars=", C".join(missing)
                )
                if missing
                else ""
            )  # fmt: skip
        )

    def band_of(self, images):
        return band_of(self.settings, images)

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


def band_of(settings, images):
    """The AAVSO band of the first image's FILTER (ARC-16: the profile's table, then the usual names); None
    when it cannot be told."""
    if not images:
        return None
    from astropy.io import fits

    from ..io.fits import readable

    try:
        name = fits.getheader(readable(images[0])).get("FILTER")
    except (OSError, ValueError):
        return None
    return profiles.aavso_band(settings, name)


def from_sequence(page, filt):
    """The AAVSO sequence's stars at the page's comparison stars and first check star (positions by the first
    frame's plate solution): (chart id, [star or None per comparison], check star or None)."""
    import numpy as np

    from ..services import aavso_vsp

    translate = QCoreApplication.translate  # pyside6-lupdate reads translate("AavsoDialog", …)
    if not page.field:
        raise ValueError(
            translate("AavsoDialog", "Identify the field first: the stars' sky positions come from its solution.")
        )
    if page.ref not in (None, 0):
        raise ValueError(
            translate("AavsoDialog", "Mark the stars on the first frame: the plate solution belongs to it.")
        )
    checks = [xy for xy, role in page.extras if role == "check"][:1]
    xy = np.array([*page.comps, *checks, page.target], float)
    ra, dec = page._field_wcs().pixel_to_world_values(xy[:, 0], xy[:, 1])
    ra0, dec0 = float(ra[-1]), float(dec[-1])
    reach = 60 * np.max(np.hypot((ra - ra0) * np.cos(np.radians(dec0)), dec - dec0))
    seq = aavso_vsp.sequence(ra0, dec0, fov=max(10.0, 2.2 * reach + 2), maglimit=17.0)
    found = aavso_vsp.sequence_magnitudes(seq, list(zip(ra[:-1], dec[:-1], strict=True)), filt)
    n = len(page.comps)
    return seq["chart"], found[:n], (found[n] if checks else None)
