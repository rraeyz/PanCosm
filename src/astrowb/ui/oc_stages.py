"""The O−C window on stages (plans/interface.md UI-16.5): Minima, Ephemeris, Model, Uncertainty, Fit and report beside
the O−C diagram, and the minima and the fitted values as the results tabs "Minima" and "Parameters"; a change of the
inputs after a fit marks both "(out of date)"."""

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QLineEdit

from . import oc_minima
from .kit.table_view import DataTable
from .stage_boxes import stages_from_boxes

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("OcWindow", "…") calls


def oc_stages(win, page):
    titles = {"minima": translate("OcWindow", "Minima"), "ephemeris": translate("OcWindow", "Ephemeris"),
              "model": translate("OcWindow", "Model"), "uncertainty": translate("OcWindow", "Uncertainty"),
              "report": translate("OcWindow", "Fit and report")}  # fmt: skip
    anchors = {"minima": "lightcurves-o-c-diagram-o", "ephemeris": "methods-ephemeris-o-c",
               "model": "lightcurves-third-body-apsidal-motion", "uncertainty": "lightcurves-third-body-apsidal-motion",
               "report": "lightcurves-reading-o-c-diagram"}  # fmt: skip
    stages_from_boxes(win, page, titles, anchors, {0: "minima", 1: "ephemeris", 2: "report", 3: "model",
                                                   4: "uncertainty"})  # fmt: skip
    minima, values = DataTable(), DataTable()
    minima.table.setObjectName("minima_table")
    values.table.setObjectName("parameters_table")
    # the tab behind the front one has a stale geometry the Tab-order check reads as "goes back up"; the filter and the
    # table in "Minima table…" keep theirs
    for edit in (*minima.findChildren(QLineEdit), minima.table):
        edit.setFocusPolicy(Qt.NoFocus)
    page.minima_view, page.parameters_view = minima, values
    win.add_result_tab("minima", translate("OcWindow", "Minima"), minima)
    win.add_result_tab("parameters", translate("OcWindow", "Parameters"), values)

    def mark(stale):
        for k in ("minima", "parameters"):
            win.set_result_stale(k, stale)

    for signal in (page.text.textChanged, page.minima_input.itemChanged, page.t0.textChanged,
                   page.period.textChanged, page.use_mcmc.toggled,
                   *(b.toggled for b in (page.linear, page.quadratic, page.ltte, page.apsidal))):  # fmt: skip
        signal.connect(lambda *_: mark(page.fit_result is not None))
    show = page.show_fit

    def show_fit(f, minima_list):
        out = show(f, minima_list)
        minima.set_data(oc_minima.header(), oc_minima.rows(f, minima_list))
        rows, _ = page.fit_table()
        values.set_data([translate("OcWindow", "Parameter"), translate("OcWindow", "Value"),
                         translate("OcWindow", "Error"), translate("OcWindow", "Unit")],
                        [[n, v, "" if e is None else e, u] for n, v, e, u in rows])  # fmt: skip
        mark(False)
        return out

    page.show_fit = show_fit
