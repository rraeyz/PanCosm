"""The Variable star search's exports (PHO-30): the candidates table as CSV, each candidate's light curve as ECSV."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QFileDialog, QPushButton

from ..photometry.varperiod import write_candidates, write_light_curves
from .messages import save_failed
from .messages import translate as message

translate = QCoreApplication.translate


def attach(page):
    """Two buttons under the candidates table, enabled once a search has a result."""
    lay = page.send.parentWidget().layout()
    table = page.export_table = QPushButton(translate("VarFind", "Save the candidates (.csv)…"), page)
    curves = page.export_curves = QPushButton(translate("VarFind", "Save their light curves (.ecsv)…"), page)
    for b in (table, curves):
        b.setEnabled(False)
        lay.addWidget(b)
    table.clicked.connect(lambda: save_table(page))
    curves.clicked.connect(lambda: save_curves(page))
    shown = page.show_result

    def show_result(out):
        shown(out)
        for b in (table, curves):
            b.setEnabled(True)

    page.show_result = show_result


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
