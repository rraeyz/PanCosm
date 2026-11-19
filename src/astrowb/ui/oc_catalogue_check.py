"""O−C stage Minima: "What changed since the catalogue ephemeris?" (plans/oc.md OC-14). The newest minima against the
T0 and period of the last catalogue look-up, kept apart from the fields the user edits."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QLabel, QPushButton

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("OcCatalogueCheck", "…") calls


def summary(r):
    """The one-line answer for the dict of catalogue_check.against."""
    if r["mean_err_min"] is None:
        line = translate("OcCatalogueCheck", "Newest {n} minima: O−C = {m:+.1f} min").format(n=r["n"], m=r["mean_min"])
    else:
        line = translate("OcCatalogueCheck", "Newest {n} minima: O−C = {m:+.1f} ± {e:.1f} min").format(
            n=r["n"], m=r["mean_min"], e=r["mean_err_min"]
        )
    if r["drift_min_per_year"] is not None:
        line += translate("OcCatalogueCheck", "; drifting {d:.1f} min a year").format(d=abs(r["drift_min_per_year"]))
    line += translate("OcCatalogueCheck", "; tonight's predictions are off by about {o:.0f} min.").format(
        o=abs(r["now_oc_min"])
    )
    return (
        line
        + " "
        + (
            translate("OcCatalogueCheck", "The catalogue ephemeris is still good for planning.")
            if r["verdict"] == "good"
            else translate("OcCatalogueCheck", "One minimum is too few to judge the ephemeris.")
            if r["verdict"] == "too few"
            else translate("OcCatalogueCheck", "The ephemeris has shifted: use the fitted one.")
        )
    )


def check(page):
    from ..timeseries.catalogue_check import against
    from .messages import translate as message
    from .oc_minima_table import minima_for_fit

    t0, period = page.catalogue
    try:
        minima = minima_for_fit(page)
        r = against([m.time for m in minima], [m.error for m in minima], t0, period, kinds=[m.kind for m in minima])
    except ValueError as e:
        page.catalogue_line.setText(message(str(e)))
        return
    page.catalogue_line.setText(summary(r))


def add_catalogue_check(page):
    """The button and the line under the Star field's stage; enabled once a look-up gave T0 and P and minima exist."""
    page.catalogue = None
    button = page.catalogue_button = QPushButton(
        translate("OcCatalogueCheck", "What changed since the catalogue ephemeris?"), page
    )
    line = page.catalogue_line = QLabel(page)
    line.setWordWrap(True)
    lay = page.stage_boxes["ephemeris"].layout()
    lay.addWidget(button)
    lay.addWidget(line)

    def refresh():
        have = bool(page.text.toPlainText().strip())
        button.setEnabled(page.catalogue is not None and have)
        button.setToolTip(
            translate("OcCatalogueCheck", "The newest minima against the catalogue ephemeris: is it still good?")
            if button.isEnabled()
            else translate("OcCatalogueCheck", "Look the star up and load minima first")
        )

    set_ephemeris = page.set_ephemeris

    def remember(target):
        set_ephemeris(target)
        if target.get("period") and target.get("t0"):
            page.catalogue = (float(target["t0"]), float(target["period"]))
        refresh()

    page.set_ephemeris = remember
    page.text.textChanged.connect(refresh)
    button.clicked.connect(lambda: check(page))
    refresh()
