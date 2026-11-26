"""The Variable star search's exports (PHO-30): the candidates table as CSV, each candidate's light curve as ECSV."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QFileDialog, QPushButton

from .. import timing
from ..photometry.varperiod import known_variables, write_candidates, write_light_curves
from .messages import save_failed
from .messages import translate as message

translate = QCoreApplication.translate


def attach(page):
    """Three buttons under the candidates table, enabled once a search has a result: the known-variable look-up
    (the only one that goes to the network, on request) and the two exports."""
    lay = page.send.parentWidget().layout()
    look = page.look_up = QPushButton(translate("VarFind", "Look up known variables"), page)
    look.setToolTip(translate("VarFind", "Solves the first frame and names the candidates found in VSX, GCVS and "
                                         "Gaia DR3 within 5″ (needs the network)"))  # fmt: skip
    look.clicked.connect(lambda: look_up(page))
    page.show_known = lambda out: show_known(page, out)
    page.known_failed = lambda msg: page.status.setText(message(msg))
    table = page.export_table = QPushButton(translate("VarFind", "Save the candidates (.csv)…"), page)
    curves = page.export_curves = QPushButton(translate("VarFind", "Save their light curves (.ecsv)…"), page)
    for b in (look, table, curves):
        b.setEnabled(False)
        lay.addWidget(b)
    table.clicked.connect(lambda: save_table(page))
    curves.clicked.connect(lambda: save_curves(page))
    shown = page.show_result

    def show_result(out):
        shown(out)
        for b in (look, table, curves):
            b.setEnabled(True)

    page.show_result = show_result


def look_up(page):
    """The frame the stars were found on (field_photometry's first, by time) to photometry.identify_field."""
    if page.result is not None and page.images:
        page.status.setText(translate("VarFind", "Looking up known variables (Gaia, VSX, GCVS)…"))
        page.known_requested.emit(timing.chronological(page.images)[0])


def show_known(page, out):
    """The identified field's catalogues matched to the candidates; the table shown again with their names."""
    r = page.result
    if r is None:
        return
    try:
        r["known_variables"] = known_variables(out["field"], [r["field"]["xy"][j] for j in page.stars], page.stars)
    except ValueError as e:
        page.status.setText(message(e))
        return
    page.show_result(r)
    k = r["known_variables"]
    n = sum(bool(a or b or c) for a, b, c in zip(k["vsx"], k["gcvs"], k["gaia_variable"], strict=True))
    page.status.setText(
        translate("VarFind", "{n} of {m} candidates are known variables.").format(n=n, m=len(k["star"]))
    )


def save_table(page, path=None):
    if page.result is None:
        return None
    if path is None:
        path, _ = QFileDialog.getSaveFileName(page, translate("VarFind", "Save the candidates"), "candidates.csv",
                                              "CSV (*.csv)")  # fmt: skip
    return _write(page, write_candidates, path) if path else None


def save_curves(page, folder=None):
    if page.result is None:
        return None
    if folder is None:
        folder = QFileDialog.getExistingDirectory(page, translate("VarFind", "Folder for the light curves"))
    return _write(page, write_light_curves, folder) if folder else None


def _write(page, write, target):
    """write(target, result): an OSError in a box (save_failed), a ValueError (a result without candidates' periods)
    and the outcome in the page's status; True, or the writer's paths, else None."""
    try:
        out = write(target, page.result)
    except OSError as e:
        return save_failed(page, e)
    except ValueError as e:
        page.status.setText(message(e))
        return None
    n = len(page.result["candidate_periods"]["star"])
    page.status.setText(translate("VarFind", "Saved {n} candidates to {path}").format(n=n, path=target))
    return True if out is None else out
