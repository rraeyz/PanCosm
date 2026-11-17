"""The Models window on stages (plans/interface.md UI-16.6): Data, System, Stars, Extras, Fit, Uncertainty beside the
light curve and its model, and the fitted values as a "Parameters" results tab. On the Visual binary tab the stages
do not apply and their dock is hidden. The posterior corner plot stays on PlotCanvas (contours are not in the plot
spec)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QGridLayout, QLayout, QVBoxLayout, QWidget

from ..models.fit import NAMES
from .kit.table_view import DataTable
from .models_history import add_history_tabs
from .stage_boxes import _current_tab_only, _index, one_per_row, stages_from_boxes

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ModelsWindow", "…") calls


def _box(page, *widgets):
    """A stage's box: the widgets moved in, out of the grids and columns the page put them in."""
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    for w in widgets:
        for old in page.findChildren(QLayout):
            old.removeWidget(w)  # a stale item in the page's hidden grid would move the widget back
        lay.addWidget(w)
    lay.addStretch(1)
    return box


def parameter_rows(page, rows):
    """The fit table's (name, value, error, unit) with the names in words (the table's first column)."""
    words = {n: page.table.item(r, 0).text() for r, n in enumerate(NAMES)}
    out = []
    for name, value, error, unit in rows:
        base, fixed = name.removesuffix(" (fixed)"), name.endswith(" (fixed)")
        label = words.get(base, base)
        out.append([translate("ModelsWindow", "{name} (fixed)").format(name=label) if fixed else label,
                    value, error, unit])  # fmt: skip
    return out


def models_stages(win, page):
    lay = page.guide.parentWidget().layout()
    grid = next(g for g in page.findChildren(QGridLayout) if g.indexOf(page.ld[0][0]) >= 0)
    lay.takeAt(_index(lay, page.ld[0][0]))  # the grid goes with the Stars stage, its exposure row to Extras
    stars = QWidget()
    QVBoxLayout(stars).setContentsMargins(0, 0, 0, 0)
    exposure_label = grid.itemAtPosition(2, 0).widget()
    for w in (exposure_label, page.exposure):
        grid.removeWidget(w)
    stars.layout().addLayout(grid)
    stars.layout().addStretch(1)
    extras = _box(page, exposure_label, page.exposure, page.use_orbit, page.overlay_button)
    fit = _box(page, page.fit_button, page.phoebe_button, page.wd_button, page.transit_button, page.results_button,
               page.status)  # fmt: skip
    for g in fit.findChildren(QGridLayout):
        one_per_row(g)
    page.stage_boxes = {"data": _box(page, page.file), "system": _box(page, page.table.parent()), "stars": stars,
                        "extras": extras, "fit": fit,
                        "uncertainty": _box(page, page.use_mcmc, page.mcmc_steps, page.posterior_button)}  # fmt: skip
    titles = {"data": translate("ModelsWindow", "Data"), "system": translate("ModelsWindow", "System"),
              "stars": translate("ModelsWindow", "Stars"), "extras": translate("ModelsWindow", "Extras"),
              "fit": translate("ModelsWindow", "Fit"),
              "uncertainty": translate("ModelsWindow", "Uncertainty")}  # fmt: skip
    anchors = {"data": "orbits-models-fitting-light-curve", "system": "orbits-models-model",
               "stars": "orbits-models-model", "extras": "orbits-models-model",
               "fit": "orbits-models-fitting-light-curve",
               "uncertainty": "orbits-models-mcmc-uncertainties"}  # fmt: skip
    stages_from_boxes(win, page, titles, anchors, {0: "data", 1: "system", 2: "fit", 3: "uncertainty"})
    page.tabs.currentChanged.connect(lambda i: win.docks["stages"].setVisible(i == 0))
    _current_tab_only(page.tabs)
    values = DataTable()
    values.table.setObjectName("parameters_table")
    page.parameters_view = values
    win.add_result_tab("parameters", translate("ModelsWindow", "Parameters"), values)
    show = page.show_fit

    def show_fit(r):
        show(r)
        rows, _ = page.fit_table()
        values.set_data([translate("ModelsWindow", "Parameter"), translate("ModelsWindow", "Value"),
                         translate("ModelsWindow", "Error"), translate("ModelsWindow", "Unit")],
                        parameter_rows(page, rows))  # fmt: skip

    page.show_fit = show_fit
    add_history_tabs(win, page)
