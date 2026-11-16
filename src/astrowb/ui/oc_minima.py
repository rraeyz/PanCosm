"""The minima of the last O−C fit as a table (plans/interface.md UI-16.5): time, error, kind, source, epoch, O−C and
the residual of the fitted model, sortable and copyable (DataTable)."""

import numpy as np
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QPushButton

from .kit.dialogs import Dialog
from .kit.table_view import DataTable

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("OcMinima", "…") calls


def rows(fit, minima):
    """One row per minimum: the fit keeps the minima's order."""
    oc, res = np.asarray(fit.o_minus_c, float) * 1440, np.asarray(fit.residuals, float) * 1440
    return [[m.time, "" if m.error is None else m.error, m.kind, m.source, int(round(e)), round(o, 3), round(r, 3)]
            for m, e, o, r in zip(minima, fit.epochs, oc, res, strict=True)]  # fmt: skip


def header():
    return [translate("OcMinima", "Time"), translate("OcMinima", "Error (d)"), translate("OcMinima", "Kind"),
            translate("OcMinima", "Source"), translate("OcMinima", "Epoch"), translate("OcMinima", "O−C (min)"),
            translate("OcMinima", "Residual (min)")]  # fmt: skip


def minima_dialog(page):
    f, minima = page.fit_result, getattr(page, "fit_minima", None)
    d = Dialog(translate("OcMinima", "Times of minimum"), page, getattr(page, "settings", None), "oc_minima")
    view = DataTable(d)
    view.set_data(header(), rows(f, minima) if f is not None and minima else [])
    d.body.addWidget(view)
    d.add_buttons(translate("OcMinima", "Close")).setDefault(True)
    d.resize(max(d.width(), 760), max(d.height(), 460))
    d.view = view
    return d


def add_result_buttons(page, layout, results_button):
    """The results' export button and "Minima table…" under it."""
    layout.addWidget(results_button)
    page.minima_button = QPushButton(translate("OcMinima", "Minima table…"), page)
    page.minima_button.setToolTip(
        translate("OcMinima", "Every minimum of the last fit with its epoch, O−C and residual")
    )
    page.minima_button.clicked.connect(lambda: minima_dialog(page).open())
    layout.addWidget(page.minima_button)
