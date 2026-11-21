"""UI-16.10: the "Sources" result tab of the Images window: the stars the existing detection (`detect_stars`, its
defaults) finds on the shown image, one row per star; a click on a row centres the viewer on it and marks it. The tab
is made at the first "Find stars" (a dock made hidden would leave a stray tab bar)."""

import numpy as np
from astropy.table import Table
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QAction

from .kit.table import TableView

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ImageWindow", "…") calls


def sources_table(data):
    """x, y (0-based array pixels) and the peak pixel value of each star, brightest first."""
    from ..photometry.fieldstars import detect_stars

    xy = detect_stars(np.asarray(data, float))
    peak = [float(data[int(round(y)), int(round(x))]) for x, y in xy]
    return Table({"x": xy[:, 0], "y": xy[:, 1], "peak": peak})


def show_star(viewer, x, y):
    viewer.set_markers([(x, y, 8.0, "lime", "")])
    viewer.centerOn(*viewer._to_scene(x, y))


def find_stars(win, page):
    """Fill the Sources tab for the shown image; the table, or None when no image is shown."""
    if page.viewer.data is None:
        return None
    table = sources_table(page.viewer.data)
    if getattr(page, "sources_view", None) is None:
        view = TableView(win)
        view.view.setObjectName("sources_table")
        view.row_chosen.connect(
            lambda i: show_star(page.viewer, float(page.sources["x"][i]), float(page.sources["y"][i]))
        )
        page.sources_view = view
        win.add_result_tab("sources", translate("ImageWindow", "Sources"), view)
    page.sources = table
    page.sources_view.set_table(table)
    return table


def find_action(win, page):
    act = QAction(translate("ImageWindow", "Find stars"), win)
    act.setToolTip(translate("ImageWindow", "List the stars found on the shown image in the Sources tab"))
    act.triggered.connect(lambda _=False: find_stars(win, page))
    return act
