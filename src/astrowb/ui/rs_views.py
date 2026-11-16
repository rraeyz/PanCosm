"""Remote sensing window extras (UI-16.13): the Histogram and Statistics result tabs of the shown band or product, and
the Export stage (the products written so far, the map as a picture)."""

import numpy as np
from PySide6.QtCore import QT_TRANSLATE_NOOP, QCoreApplication, Qt
from PySide6.QtWidgets import QFileDialog, QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget

from ..remotesensing import analysis
from .kit.table_view import DataTable
from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("RemoteSensingWindow", "…") calls

STATS = (("n", QT_TRANSLATE_NOOP("RemoteSensingWindow", "Pixels")),
         ("min", QT_TRANSLATE_NOOP("RemoteSensingWindow", "Minimum")), ("p2", "2 %"), ("p25", "25 %"),
         ("median", QT_TRANSLATE_NOOP("RemoteSensingWindow", "Median")), ("p75", "75 %"), ("p98", "98 %"),
         ("max", QT_TRANSLATE_NOOP("RemoteSensingWindow", "Maximum")),
         ("mean", QT_TRANSLATE_NOOP("RemoteSensingWindow", "Mean")),
         ("std", QT_TRANSLATE_NOOP("RemoteSensingWindow", "Standard deviation")))  # fmt: skip


def histogram_figure(data, label, bins=64, sample=4_000_000):
    """Pixel counts of a band or product (finite pixels, an even sample of at most `sample`), or None when empty."""
    flat = np.asarray(data, np.float32).ravel()
    v = flat[:: max(1, flat.size // sample)]
    v = v[np.isfinite(v)]
    if v.size == 0:
        return None
    counts, edges = np.histogram(v, bins=bins)
    axes = (AxisSpec(label), AxisSpec(translate("RemoteSensingWindow", "Pixels")))
    return FigureSpec([PanelSpec(*axes, [SeriesSpec(label, edges, counts, kind="histogram", alpha=0.6)])])


def statistics_rows(data):
    """[name, value] rows of analysis.statistics, in words; empty when no pixel is finite."""
    st = analysis.statistics(data)
    return [
        [translate("RemoteSensingWindow", name) if name[0].isalpha() else name, st[key]]
        for key, name in STATS
        if key in st
    ]


def export_stage(page):
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(QLabel(translate("RemoteSensingWindow", "Products written (GeoTIFF, next to the image)"), box))
    page.products_list = QListWidget(box)
    page.products_list.setToolTip(translate("RemoteSensingWindow", "Every result is saved as a georeferenced GeoTIFF"))
    lay.addWidget(page.products_list, 1)
    page.picture_button = QPushButton(translate("RemoteSensingWindow", "Save the map as a picture…"), box)
    page.picture_button.setToolTip(translate("RemoteSensingWindow", "The map as it is on screen, as a PNG file"))
    page.picture_button.clicked.connect(lambda: save_picture(page))
    lay.addWidget(page.picture_button)
    return box


def save_picture(page):
    path, _ = QFileDialog.getSaveFileName(page, "", "map.png", "PNG (*.png)")
    if path and not page.viewer.grab().save(path):
        page.status.setText(translate("RemoteSensingWindow", "Cannot write {path}").format(path=path))


def add_views(win, page):
    """Histogram and Statistics tabs under the map, refreshed when another band or product is shown; the Export
    stage lists the products as they are saved."""
    from .plot.toolbar import plot_box

    hist_box, hist = plot_box(win)
    table = DataTable()
    page.histogram_view, page.statistics_view = hist, table
    first = win.add_result_tab("histogram", translate("RemoteSensingWindow", "Histogram"), hist_box)
    win.add_result_tab("statistics", translate("RemoteSensingWindow", "Statistics"), table)
    win.resizeDocks([first], [220], Qt.Vertical)  # the plot's size hint would otherwise leave the map 120 px

    def refresh(name):
        if not name:
            return
        data = page._current()
        if data is None:
            return
        fig = histogram_figure(data, name)
        if fig is not None:
            hist.set_figure(fig)
        table.set_data([translate("RemoteSensingWindow", "Statistic"), translate("RemoteSensingWindow", "Value")],
                       statistics_rows(data))  # fmt: skip

    shown = page._show

    def show_band(name):  # open() and show_product() call _show directly, the combo box through its signal
        shown(name)
        refresh(name)

    page.show_combo.currentTextChanged.disconnect(shown)
    page._show = show_band
    page.show_combo.currentTextChanged.connect(show_band)
    show = page.show_product

    def show_product(product):
        show(product)
        page.products_list.addItem(product["path"])

    page.show_product = show_product
    from .kit.focus import read_in_order

    for w in (hist_box, *hist_box.findChildren(QWidget)):
        w.setFocusPolicy(Qt.NoFocus)  # a tab behind the other sits off-screen: Tab would jump back up to it
    read_in_order(*win.stage_panels.values(), page.viewer, page.plot, table)  # Tab follows the screen
