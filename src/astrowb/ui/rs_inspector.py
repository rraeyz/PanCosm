"""Remote sensing (UI-16.13): the inspector with the band values and the spectrum of the clicked pixel, hidden until a
pixel is chosen. Only what the scene holds: its band values, names and georeference (it carries no band wavelengths,
so the spectrum's x axis is the band number)."""

import numpy as np
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from ..remotesensing import analysis
from .kit.inspector import Inspector
from .plot.spec import AxisSpec, FigureSpec, PanelSpec, SeriesSpec

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("RemoteSensingWindow", "…") calls


def pixel_rows(r, x, y):
    """[(name, value, unit)] of image pixel (x, y): its position, the longitude and latitude when the scene is
    georeferenced, then the value of every band."""
    rows = [("x", x, "px"), ("y", y, "px")]
    try:
        ll = r.lonlat(x + 0.5, y + 0.5)
    except Exception:  # unknown or unsupported CRS: no longitude and latitude
        ll = None
    if ll:
        rows += [(translate("RemoteSensingWindow", "Longitude"), float(ll[0]), "°"),
                 (translate("RemoteSensingWindow", "Latitude"), float(ll[1]), "°")]  # fmt: skip
    spec = r.pixel(x, y) if hasattr(r, "pixel") else analysis.pixel_spectrum(r.bands, x, y)
    return rows + [(n, float(v), "") for n, v in zip(r.names, np.asarray(spec).tolist(), strict=False)]


def spectrum_figure(r, x, y):
    """Value against the band number of one pixel (the scene holds no band wavelengths)."""
    spec = np.asarray(r.pixel(x, y) if hasattr(r, "pixel") else analysis.pixel_spectrum(r.bands, x, y), float)
    bands = np.arange(1, len(spec) + 1)
    name = translate("RemoteSensingWindow", "Pixel {x}, {y}").format(x=x, y=y)
    ticks = list(zip(bands.tolist(), r.names, strict=False)) if len(spec) <= 16 else None
    series = [SeriesSpec(name, bands, spec, size=5), SeriesSpec(name, bands, spec, kind="line")]
    return FigureSpec([PanelSpec(AxisSpec(translate("RemoteSensingWindow", "Band"), ticks=ticks),
                                 AxisSpec(translate("RemoteSensingWindow", "Value")), series)])  # fmt: skip


def pixel_inspector(win, page):
    from .plot.toolbar import plot_box

    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    panel = Inspector(translate("RemoteSensingWindow", "Pixel"))
    plot_widget, view = plot_box(box)
    lay.addWidget(panel)
    lay.addWidget(plot_widget, 1)
    for w in (plot_widget, *plot_widget.findChildren(QWidget)):
        w.setFocusPolicy(Qt.NoFocus)
    dock = win.set_inspector(box)
    dock.hide()

    def show(x, y):
        r = page.raster
        if r is None:
            return
        x, y = page._pixel(x + 0.5, y + 0.5)  # clicked gives 0-based pixel centres
        if not (0 <= y < r.shape[0] and 0 <= x < r.shape[1]):
            return
        panel.set_title(translate("RemoteSensingWindow", "Pixel {x}, {y}").format(x=x, y=y))
        panel.set_rows(pixel_rows(r, x, y))
        view.set_figure(spectrum_figure(r, x, y))
        dock.show()

    page.viewer.clicked.connect(show)
    win.pixel_inspector, page.pixel_view = panel, view
