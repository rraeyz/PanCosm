"""The "Correlations" results tab of the O−C window (plans/interface.md UI-16.5): the correlation matrix of the fitted
parameters, strongly tied pairs (|r| > 0.9) marked. Added to the window at the first fit that has a matrix."""

from PySide6.QtCore import QCoreApplication

from .kit import tokens
from .kit.table_view import DataTable

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("OcWindow", "…") calls
TIED = 0.9


def show_correlations(win, page, corr):
    """Fill (and on the first call add) the tab from the fit's {"names", "matrix"}; None empties it."""
    view = getattr(page, "correlations_view", None)
    if view is None:
        if not corr:
            return
        view = page.correlations_view = DataTable()
        view.table.setObjectName("correlations_table")
        win.add_result_tab("correlations", translate("OcWindow", "Correlations"), view)
    names, matrix = (corr["names"], corr["matrix"]) if corr else ([], [])
    view.set_data([translate("OcWindow", "Parameter"), *names],
                  [[n, *[f"{r:.3f}" for r in row]] for n, row in zip(names, matrix, strict=True)])  # fmt: skip
    view.table.setSortingEnabled(False)  # a matrix: rows keep their place, so the marks below land on their cells
    why = translate("OcWindow", "|r| > 0.9: these two parameters are tied; their errors are not independent")
    for i, row in enumerate(matrix):
        for j, r in enumerate(row):
            if i != j and abs(r) > TIED:
                view.mark(i, j + 1, tokens.role("saturated"), why)
