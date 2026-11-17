"""Remote sensing map layers (UI-16.13): a longitude / latitude grid, a scale bar and a north arrow over the map, each
with a check box under the Layers list. Everything comes from the scene's georeference; a layer the scene cannot give
is disabled with a tooltip saying why."""

import math

import numpy as np
from PySide6.QtCore import QCoreApplication, QPointF
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import QCheckBox, QGraphicsPathItem, QGraphicsSimpleTextItem, QVBoxLayout, QWidget

from .kit import tokens

translate = QCoreApplication.translate

NAMES = ("Grid", "Scale bar", "North arrow")
# degree steps: whole degrees, then arc-minutes and arc-seconds that divide the degree evenly
STEPS = [30, 10, 5, 2, 1, 0.5, 1 / 6, 1 / 12, 1 / 30, 1 / 60, 1 / 120, 1 / 360, 1 / 720, 1 / 3600]


def pixel_size_m(r):
    """Metres per pixel when the scene holds a transform in a CRS measured in metres, else None."""
    if r is None or r.transform is None or not r.epsg:
        return None
    try:
        from pyproj import CRS

        if CRS.from_epsg(r.epsg).axis_info[0].unit_name not in ("metre", "meter"):
            return None
    except Exception:  # unknown CRS
        return None
    _, a, b, _, d, e = r.transform
    return math.sqrt(abs(a * e - b * d))


def nice_length(metres):
    """The round number (1, 2 or 5 × 10^n) not above `metres`."""
    p = 10 ** math.floor(math.log10(metres))
    return max(m * p for m in (1, 2, 5) if m * p <= metres)


def has_lonlat(r):
    if r is None:
        return False
    try:
        return r.lonlat(0.5, 0.5) is not None
    except Exception:  # unknown or unsupported CRS
        return False


def north_direction(r):
    """Unit vector (dx, dy) of north at the image centre in picture pixels (x right, y down), from the longitude /
    latitude of the centre and of the pixels 5 to its right and 5 below it."""
    ny, nx = r.shape
    c, row = nx / 2, ny / 2
    ll0 = r.lonlat(c, row)
    cos = math.cos(math.radians(ll0[1]))
    right, down = (((p[0] - ll0[0]) * cos, p[1] - ll0[1]) for p in (r.lonlat(c + 5, row), r.lonlat(c, row + 5)))
    det = right[0] * down[1] - down[0] * right[1]
    p, q = -down[0] / det, right[0] / det  # north (0, 1) = p * right + q * down
    n = math.hypot(p, q)
    return p / n, q / n


def _to_pixel(r):
    """Function (lon, lat) -> (column, row) inverting the scene's transform."""
    from pyproj import Transformer

    c, a, b, f, d, e = r.transform
    inv = np.linalg.inv([[a, b], [d, e]])
    tr = Transformer.from_crs(4326, r.epsg, always_xy=True)

    def convert(lon, lat):
        x, y = tr.transform(lon, lat)
        col, row = inv @ [x - c, y - f]
        return float(col), float(row)

    return convert


def grid_lines(r, col0, row0, col1, row1, target=5):
    """[(("lon" | "lat", degrees), [(col, row), ...])]: meridians and parallels over a window of the picture (columns
    and rows from the top), a round number of degrees or minutes apart, about `target` across the window."""
    xs, ys = np.linspace(col0, col1, 9), np.linspace(row0, row1, 9)
    ll = np.array([r.lonlat(x, y) for y in ys for x in xs])
    (lon0, lat0), (lon1, lat1) = ll.min(axis=0), ll.max(axis=0)
    span = max(lon1 - lon0, lat1 - lat0)
    step = next((s for s in STEPS if span / s >= target), STEPS[-1])
    convert, lines = _to_pixel(r), []
    for v in np.arange(math.ceil(lon0 / step) * step, lon1, step):
        lines.append((("lon", float(v)), [convert(v, w) for w in np.linspace(lat0, lat1, 24)]))
    for v in np.arange(math.ceil(lat0 / step) * step, lat1, step):
        lines.append((("lat", float(v)), [convert(w, v) for w in np.linspace(lon0, lon1, 24)]))
    return lines


def _pen(colour):
    pen = QPen(QColor(colour))
    pen.setCosmetic(True)
    return pen


class MapLayers:
    """The three check boxes and their scene items for one RemoteSensingPage."""

    def __init__(self, page):
        self.page, self.items, self.boxes = page, [], {}
        self.widget = QWidget(page)
        h = QVBoxLayout(self.widget)  # the stages column is narrow
        h.setContentsMargins(0, 0, 0, 0)
        labels = (
            translate("RemoteSensingWindow", "Grid"),
            translate("RemoteSensingWindow", "Scale bar"),
            translate("RemoteSensingWindow", "North arrow"),
        )
        for name, text in zip(NAMES, labels, strict=True):
            box = QCheckBox(text, self.widget)
            box.setToolTip(translate("RemoteSensingWindow", "Show this on the map"))
            box.toggled.connect(self.redraw)
            h.addWidget(box)
            self.boxes[name] = box
        page.viewer.view_changed.connect(self.redraw)

    def refresh(self):
        """Enable each layer only when the scene can give it, and say why not."""
        r = self.page.raster
        ok = {"Grid": has_lonlat(r), "Scale bar": pixel_size_m(r) is not None, "North arrow": has_lonlat(r)}
        why = {
            "Grid": translate("RemoteSensingWindow", "The scene has no georeference that gives longitude and latitude"),
            "Scale bar": translate("RemoteSensingWindow", "The scene holds no pixel size in metres"),
            "North arrow": translate("RemoteSensingWindow", "The scene has no georeference that gives north"),
        }
        for name, box in self.boxes.items():
            box.setEnabled(ok[name])
            box.setToolTip(translate("RemoteSensingWindow", "Show this on the map") if ok[name] else why[name])
            if not ok[name]:
                box.setChecked(False)
        self.redraw()

    def _add(self, item):
        self.page.viewer.scene().addItem(item)
        self.items.append(item)

    def _label(self, text, pos, colour):
        item = QGraphicsSimpleTextItem(text)
        item.setBrush(QColor(colour))
        item.setPos(pos)
        item.setFlag(QGraphicsSimpleTextItem.ItemIgnoresTransformations)
        self._add(item)

    def _path(self, path, colour):
        item = QGraphicsPathItem(path)
        item.setPen(_pen(colour))
        self._add(item)

    def redraw(self, *_):
        viewer, r = self.page.viewer, self.page.raster
        for item in self.items:
            viewer.scene().removeItem(item)
        self.items = []
        if r is None or viewer.data is None:
            return
        ny = r.shape[0]
        rect = viewer.mapToScene(viewer.viewport().rect()).boundingRect()
        col0, col1 = max(rect.left(), 0), min(rect.right(), r.shape[1])
        row0, row1 = max(ny - rect.bottom(), 0), min(ny - rect.top(), ny)  # scene y runs up, rows run down
        colour = tokens.role("non_linear")
        zoom = abs(viewer.transform().m11()) or 1.0
        if self.boxes["Grid"].isChecked() and col1 > col0 and row1 > row0:
            self._grid(r, (col0, row0, col1, row1), colour)
        if self.boxes["Scale bar"].isChecked():
            self._scale_bar(r, rect, zoom, colour)
        if self.boxes["North arrow"].isChecked():
            self._arrow(r, rect, zoom, colour)

    def _grid(self, r, window, colour):
        ny = r.shape[0]
        for (kind, value), pts in grid_lines(r, *window):
            path = QPainterPath()
            path.moveTo(pts[0][0], ny - pts[0][1])
            for c, w in pts[1:]:
                path.lineTo(c, ny - w)
            self._path(path, colour)
            hemisphere = ("EW" if kind == "lon" else "NS")[value < 0]
            self._label(f"{abs(value):.6g}°{hemisphere}", QPointF(pts[0][0], ny - pts[0][1]), colour)

    def _scale_bar(self, r, rect, zoom, colour):
        size = pixel_size_m(r)
        metres = nice_length(0.25 * rect.width() * size)
        length = metres / size  # picture pixels
        x1, y = rect.right() - 20 / zoom, rect.bottom() - 20 / zoom
        path = QPainterPath()
        path.moveTo(x1 - length, y)
        path.lineTo(x1, y)
        self._path(path, colour)
        self._label(f"{metres / 1000:g} km" if metres >= 1000 else f"{metres:g} m", QPointF(x1 - length, y), colour)

    def _arrow(self, r, rect, zoom, colour):
        dx, dy = north_direction(r)  # picture pixels, y down; the scene's y runs up
        v = QPointF(dx, -dy) * (32 / zoom)
        o = QPointF(rect.left() + 46 / zoom, rect.bottom() - 46 / zoom)
        side = QPointF(-v.y(), v.x()) * 0.25
        path = QPainterPath()
        path.moveTo(o)
        path.lineTo(o + v)
        path.lineTo(o + v * 0.7 + side)
        path.moveTo(o + v)
        path.lineTo(o + v * 0.7 - side)
        self._path(path, colour)
        self._label("N", o + v * 1.15, colour)


def install(page, layers):
    """Put the three map layers' check boxes under the layers list; returns the MapLayers (refresh per shown band)."""
    page.map_layers = MapLayers(page)
    layers.layout().addWidget(page.map_layers.widget)
    return page.map_layers
