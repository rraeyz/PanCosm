"""Remote sensing Layers list (UI-16.13): every band and product of the page with a visibility box and an opacity
slider; the map shows the visible layers drawn in list order (the first row at the bottom), each over the ones below."""

import numpy as np
from PySide6.QtCore import QCoreApplication, Qt, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QScrollArea, QSlider, QVBoxLayout, QWidget

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("RemoteSensingWindow", "…") calls


def compose(pictures):
    """[(uint8 grey or RGB picture, opacity 0-1)] bottom to top: alpha-over on black, as uint8 RGB."""
    out = None
    for pic, alpha in pictures:
        rgb = np.asarray(pic, np.float32)
        rgb = np.repeat(rgb[..., None], 3, axis=2) if rgb.ndim == 2 else rgb
        out = rgb * alpha if out is None else out * (1 - alpha) + rgb * alpha
    return np.ascontiguousarray(np.rint(out).astype(np.uint8))


class LayersList(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rs_layers")
        self.rows = {}  # name -> (visible box, opacity slider)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(translate("RemoteSensingWindow", "Layers"), self))
        self.setToolTip(translate("RemoteSensingWindow", "The map shows the ticked layers, the lower ones first"))
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(150)
        self.body = QWidget(scroll)
        self.column = QVBoxLayout(self.body)
        self.column.addStretch(1)
        scroll.setWidget(self.body)
        lay.addWidget(scroll)

    def sync(self, names):
        """One row per name in this order; the rows already there keep their state."""
        for name in [n for n in self.rows if n not in names]:
            for w in self.rows.pop(name):
                w.parentWidget().deleteLater()
        for name in names:
            if name not in self.rows:
                self._add(name)

    def _add(self, name):
        row = QWidget(self.body)
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        box = QCheckBox(name, row)
        box.setToolTip(translate("RemoteSensingWindow", "Show this layer on the map"))
        slider = QSlider(Qt.Horizontal, row)
        slider.setRange(0, 100)
        slider.setValue(100)
        slider.setToolTip(translate("RemoteSensingWindow", "Opacity of this layer"))
        h.addWidget(box, 1)
        h.addWidget(slider, 1)
        box.toggled.connect(self.changed)
        slider.valueChanged.connect(self.changed)
        self.column.insertWidget(len(self.rows), row)
        self.rows[name] = (box, slider)

    def set_only(self, name):
        """Only this layer visible, at full opacity (the band chosen in Show); no signal."""
        self.blockSignals(True)
        for n, (box, slider) in self.rows.items():
            box.setChecked(n == name)
            slider.setValue(100)
        self.blockSignals(False)

    def state(self):
        """[(name, opacity 0-1)] of the visible layers, in list order."""
        return [(n, s.value() / 100) for n, (b, s) in self.rows.items() if b.isChecked() and s.value() > 0]


def draw(page):
    """The map from the visible layers (a black picture when none is visible)."""
    from ..display import render

    viewer, shown = page.viewer, []
    for name, alpha in page.layers.state():
        data = page._current(name)
        if data is None or (shown and data.shape != shown[0][1].shape):
            continue
        filled = np.nan_to_num(data, nan=float(np.nanmin(data)) if np.isfinite(data).any() else 0.0)
        shown.append((name, np.flipud(filled), alpha))
    if not shown:
        shown = [("", np.zeros((page.raster.shape[0], page.raster.shape[1]), np.float32), 1.0)]
    if len(shown) == 1 and shown[0][2] == 1.0:
        viewer.set_image(shown[0][1], keep_view=True)
        return
    args = (viewer.interval, viewer.stretch, None, viewer.cmap, viewer.invert)
    pic = compose([(render(d, *args), a) for _, d, a in shown])
    top = shown[-1][1]  # the pixel read-out reports the top layer
    viewer.data = top
    viewer.scene().setSceneRect(0, 0, top.shape[1], top.shape[0])
    viewer._show(pic)


def install(page):
    """Put the Layers list in the page's column under the stages and keep it in step with the Show box."""
    from .stage_boxes import _index

    lay = page.readout.parentWidget().layout()
    page.layers = LayersList(page)
    lay.insertWidget(_index(lay, page.readout), page.layers)
    shown = page._show

    def show(name):
        shown(name)
        page.layers.sync([page.show_combo.itemText(i) for i in range(page.show_combo.count())])
        page.layers.set_only(name)

    page.show_combo.currentTextChanged.disconnect(shown)
    page._show = show
    page.show_combo.currentTextChanged.connect(show)
    page.layers.changed.connect(lambda: draw(page) if page.raster is not None else None)
