"""The Models window's Prior column (plans/interface.md UI-16.6): Uniform (the default, flat between the limits) or
Log-uniform per parameter. The choices go to models.eb_fit as `priors`; the MCMC applies them."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QComboBox

from ..models import fit

translate = QCoreApplication.translate
PRIOR = 5
KINDS = ("uniform", "log-uniform")


def header():
    return [translate("ModelsWindow", "Prior")]


def add_combo(page, row):
    box = QComboBox(page.table)
    box.addItems([translate("ModelsWindow", "Uniform"), translate("ModelsWindow", "Log-uniform")])
    box.setToolTip(translate("ModelsWindow", "Prior of the MCMC between the limits; log-uniform needs positive limits"))

    def changed(_i):
        if not (page._restoring or page._editing):  # like a typed value: one undo step
            page.record(translate("ModelsWindow", "Change a prior"), page._typed_from)
            page._typed_from = page.undo_state()

    box.currentIndexChanged.connect(changed)
    page.table.setCellWidget(row, PRIOR, box)


def kinds(table, names):
    return tuple(KINDS[table.cellWidget(r, PRIOR).currentIndex()] for r in range(len(names)))


def set_kinds(table, values):
    for r, kind in enumerate(values):
        table.cellWidget(r, PRIOR).setCurrentIndex(KINDS.index(kind))


def read(table, names, bounds):
    """{name: "log-uniform"} for the rows set so (empty when none); ValueError when a limit rules it out."""
    out = {n: k for n, k in zip(names, kinds(table, names), strict=True) if k != "uniform"}
    fit.log_uniform_names(out, bounds)
    return out
