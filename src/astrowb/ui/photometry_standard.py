"""The Photometry page's standard-magnitudes row: the images' filter, where the comparison magnitudes come from
(the catalogues, or the field's AAVSO sequence; plans/photometry.md PHO-25 item 3) and the button that looks them up.
Magnitudes typed into the star table stay the manual way."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("PhotometryStandard", "…") calls


def add_row(page, layout):
    row = QHBoxLayout()
    page.band = QComboBox(page)
    page.band.addItems(("V", "B", "R", "I", "G", "SG", "SR", "SI", "CV"))
    page.band.setToolTip(translate("PhotometryStandard", "Filter of the images (CV: unfiltered, reduced to V)"))
    page.mag_source = QComboBox(page)
    page.mag_source.addItem(translate("PhotometryStandard", "Gaia GSPC / APASS / Gaia"), "auto")
    page.mag_source.addItem(translate("PhotometryStandard", "APASS / Gaia GSPC / Gaia"), "apass")
    page.mag_source.addItem(translate("PhotometryStandard", "AAVSO sequence"), "aavso")
    page.mag_source.setToolTip(
        translate(
            "PhotometryStandard",
            "Where the comparison magnitudes come from: the catalogues (Gaia's synthetic Johnson-Cousins "
            "photometry, else APASS, else Gaia's colours), or the field's AAVSO chart, as AAVSO reports ask",
        )
    )
    page.catalog_button = QPushButton(translate("PhotometryStandard", "Standard magnitudes"), page)
    page.catalog_button.setToolTip(
        translate(
            "PhotometryStandard",
            "Looks up the comparison stars (needs the internet once and a plate-solved first image) and turns the "
            "light curve into magnitudes in the standard system",
        )
    )
    page.catalog_button.setEnabled(False)
    page.catalog_button.clicked.connect(page._catalog)
    row.addWidget(page.band)
    row.addWidget(page.mag_source)
    row.addWidget(page.catalog_button, 1)
    layout.addLayout(row)


def params(page):
    return {"filter": page.band.currentText(), "source": page.mag_source.currentData()}
