"""Image viewer: pan (drag), zoom (wheel), stretch, pixel read-out."""

import numpy as np
from PySide6.QtCore import QPoint, QPointF, Qt, Signal
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView

from ..display import render

RETICLE = 9  # screen pixels: radius of the fixed-size ring around a marked star on a zoomed-out frame


class ImageViewer(QGraphicsView):
    # FITS 1-based pixel coordinates and the value under the cursor
    hovered = Signal(float, float, float)
    # a click without dragging, in 0-based array coordinates (x = column, y = row; pixel centres on integers)
    clicked = Signal(float, float)
    context_requested = Signal(float, float, QPoint)  # array x, y and the screen position of a right click
    # with the "area" or "line" tool: the two ends of the drag, 0-based array coordinates
    region_selected = Signal(float, float, float, float)
    line_selected = Signal(float, float, float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self._item = QGraphicsPixmapItem()
        self._item.setTransformationMode(Qt.FastTransformation)  # show real pixels when zoomed in
        self.scene().addItem(self._item)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setRenderHint(QPainter.SmoothPixmapTransform, False)
        self.setBackgroundBrush(Qt.black)
        self.setMouseTracking(True)
        self.data = None
        self.interval, self.stretch = "zscale", "linear"
        self.limits, self.cmap, self.invert = None, "grey", False
        self._fit_mode = True  # keep the image fitted to the window until the user zooms
        self._press = None
        self._markers, self.marker_list = [], []
        self._overlays = {}  # name -> graphics items (contours, grid, catalogue, regions)
        self.tool = "pan"  # pan | aperture (clicks) | area | line (drags)
        self._drag_start, self._rubber = None, None
        self._pick, self._hover_rings, self._hover_items = False, [], []

    def set_image(self, data: np.ndarray):
        for name in list(self._overlays):  # overlays belong to the previous image
            self.set_overlay(name)
        self.data = data
        self.refresh()
        self.fit()

    def clear(self):
        """No image shown (the last open image was closed)."""
        for name in list(self._overlays):
            self.set_overlay(name)
        self.data = None
        self._item.setPixmap(QPixmap())

    def set_stretch(self, interval=None, stretch=None):
        self.interval = interval or self.interval
        self.stretch = stretch or self.stretch
        self.refresh()

    def set_levels(self, limits=None, cmap=None, invert=None):
        """Manual black / white levels in data units (None: from the interval), colour map, inverted display."""
        self.limits = limits
        self.cmap = cmap if cmap is not None else self.cmap
        self.invert = invert if invert is not None else self.invert
        self.refresh()

    def refresh(self):
        if self.data is None:
            return
        pic = render(self.data, self.interval, self.stretch, self.limits, self.cmap, self.invert)  # FITS y up
        h, w = pic.shape[:2]
        if pic.ndim == 2:
            qimg = QImage(pic.data, w, h, w, QImage.Format_Grayscale8).copy()  # copy: numpy buffer is freed later
        else:
            qimg = QImage(pic.data, w, h, 3 * w, QImage.Format_RGB888).copy()
        self._item.setPixmap(QPixmap.fromImage(qimg))
        self.scene().setSceneRect(0, 0, w, h)

    def fit(self):
        self._fit_mode = True
        self.fitInView(self._item, Qt.KeepAspectRatio)
        self._update_reticles()

    def zoom(self, factor: float):
        self._fit_mode = False
        self.scale(factor, factor)
        self._update_reticles()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit_mode and self.data is not None:
            self.fitInView(self._item, Qt.KeepAspectRatio)
        self._update_reticles()

    def _update_reticles(self):
        """Fixed-size rings only where the real rings are small on screen; zoomed in, the real rings speak."""
        scale = abs(self.transform().m11()) or 1.0
        for item in getattr(self, "_markers", []):
            r = item.data(0)
            if r is not None:
                item.setVisible(r * scale < RETICLE)
        for item in getattr(self, "_hover_items", []):
            r = item.data(0)
            if r is not None:
                item.setVisible(r * scale < RETICLE)

    def wheelEvent(self, event):
        self.zoom(1.25 if event.angleDelta().y() > 0 else 0.8)

    def _to_scene(self, x, y):
        return x + 0.5, self.data.shape[0] - 0.5 - y

    def set_markers(self, markers):
        """markers: [(x, y, radius, colour name, label)] or (..., label, "dash") in 0-based array coordinates."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor, QPen, QTransform
        from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsSimpleTextItem

        for item in self._markers:
            self.scene().removeItem(item)
        self._markers = []
        self.marker_list = list(markers)  # kept for saving as DS9 regions
        if self.data is None:
            return
        biggest = {}
        for x, y, r, colour, *_ in markers:
            biggest[(x, y)] = (max(r, biggest.get((x, y), (0, ""))[0]), colour)
        for (x, y), (r, colour) in biggest.items():
            # a ring of fixed screen size around each marked star, shown while its real rings are only a few screen
            # pixels across (a large frame fitted to the window): the user always sees which stars are marked
            sx, sy = self._to_scene(x, y)
            reticle = QGraphicsEllipseItem(-RETICLE, -RETICLE, 2 * RETICLE, 2 * RETICLE)
            pen = QPen(QColor(colour))
            pen.setWidth(2)
            pen.setCosmetic(True)
            reticle.setPen(pen)
            reticle.setPos(sx, sy)
            reticle.setFlag(QGraphicsEllipseItem.ItemIgnoresTransformations)
            reticle.setData(0, r)
            self.scene().addItem(reticle)
            self._markers.append(reticle)
        self._update_reticles()
        for x, y, r, colour, label, *style in markers:
            sx, sy = self._to_scene(x, y)
            circle = QGraphicsEllipseItem(sx - r, sy - r, 2 * r, 2 * r)
            pen = QPen(QColor(colour))
            pen.setCosmetic(True)  # 1 screen pixel wide at any zoom
            if style == ["dash"]:
                pen.setStyle(Qt.DashLine)
            circle.setPen(pen)
            text = QGraphicsSimpleTextItem(label)
            text.setBrush(QColor(colour))
            text.setPos(sx + r, sy - r)
            text.setFlag(QGraphicsSimpleTextItem.ItemIgnoresTransformations)
            text.setTransform(QTransform.fromTranslate(4, -16))  # screen pixels: clear of the fixed-size ring
            for item in (circle, text):
                self.scene().addItem(item)
                self._markers.append(item)

    def set_overlay(self, name, colour="#00e5ff", lines=(), circles=(), texts=()):
        """Draw a named layer (replacing the old one): polylines [[(x, y), ...]], circles [(x, y, r, label)],
        texts [(x, y, text)], all in 0-based array coordinates. Empty lists remove the layer."""
        from PySide6.QtGui import QColor, QPainterPath, QPen
        from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsSimpleTextItem

        for item in self._overlays.pop(name, []):
            self.scene().removeItem(item)
        if self.data is None:
            return
        pen = QPen(QColor(colour))
        pen.setCosmetic(True)
        items = []
        if lines:
            path = QPainterPath()
            for line in lines:
                path.moveTo(*self._to_scene(*line[0]))
                for x, y in line[1:]:
                    path.lineTo(*self._to_scene(x, y))
            items.append(QGraphicsPathItem(path))
            items[-1].setPen(pen)
        for x, y, r, label in circles:
            sx, sy = self._to_scene(x, y)
            items.append(QGraphicsEllipseItem(sx - r, sy - r, 2 * r, 2 * r))
            items[-1].setPen(pen)
            if label:
                texts = [*texts, (x + r, y + r, label)]
        for x, y, text in texts:
            t = QGraphicsSimpleTextItem(str(text))
            t.setBrush(QColor(colour))
            t.setPos(*self._to_scene(x, y))
            t.setFlag(QGraphicsSimpleTextItem.ItemIgnoresTransformations)
            items.append(t)
        for item in items:
            self.scene().addItem(item)
        if items:
            self._overlays[name] = items

    def overlay_names(self):
        return sorted(self._overlays)

    def set_pick(self, on, rings=(), colour="lime"):
        """Clicking marks stars (photometry): a cross cursor instead of the hand, and the rings that a click would
        place drawn under the mouse, [(radius in pixels, dashed)]. Dragging still moves the image."""
        self._pick, self._hover_rings, self._hover_colour = on, list(rings), colour
        self.viewport().setCursor(Qt.CrossCursor if on else Qt.OpenHandCursor)
        self._clear_hover()

    def _clear_hover(self):
        for item in self._hover_items:
            self.scene().removeItem(item)
        self._hover_items = []

    def _draw_hover(self, sx, sy):
        from PySide6.QtGui import QColor, QPen
        from PySide6.QtWidgets import QGraphicsEllipseItem

        if not self._hover_items:
            for r, dashed in self._hover_rings:
                item = QGraphicsEllipseItem(-r, -r, 2 * r, 2 * r)
                pen = QPen(QColor(self._hover_colour))
                pen.setCosmetic(True)
                pen.setStyle(Qt.DashLine if dashed else Qt.SolidLine)
                item.setPen(pen)
                item.setOpacity(0.7)
                self.scene().addItem(item)
                self._hover_items.append(item)
            if self._hover_rings:  # the fixed-size ring that shows where a click lands on a zoomed-out frame
                reticle = QGraphicsEllipseItem(-RETICLE, -RETICLE, 2 * RETICLE, 2 * RETICLE)
                pen = QPen(QColor(self._hover_colour))
                pen.setWidth(2)
                pen.setCosmetic(True)
                reticle.setPen(pen)
                reticle.setFlag(QGraphicsEllipseItem.ItemIgnoresTransformations)
                reticle.setData(0, max(r for r, _ in self._hover_rings))
                self.scene().addItem(reticle)
                self._hover_items.append(reticle)
            self._update_reticles()
        for item in self._hover_items:
            item.setPos(sx, sy)

    def leaveEvent(self, event):
        self._clear_hover()
        super().leaveEvent(event)

    def set_tool(self, tool):
        """pan: drag moves the image; aperture: clicks; area / line: drag draws a rectangle / line."""
        self.tool = tool
        self.setDragMode(QGraphicsView.ScrollHandDrag if tool == "pan" else QGraphicsView.NoDrag)
        self.viewport().setCursor(Qt.OpenHandCursor if tool == "pan" else Qt.CrossCursor)

    def _array_xy(self, pos):
        p = self.mapToScene(pos.toPoint())
        return p.x() - 0.5, self.data.shape[0] - 0.5 - p.y()

    def show_selection(self, kind, x0, y0, x1, y1):
        """Keep the measured rectangle or line drawn (0-based array coordinates); kind None removes it."""
        from PySide6.QtGui import QColor, QPen
        from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsRectItem

        if self._rubber is not None:
            self.scene().removeItem(self._rubber)
            self._rubber = None
        if kind is None or self.data is None:
            return
        (ax, ay), (bx, by) = self._to_scene(x0, y0), self._to_scene(x1, y1)
        if kind == "area":
            item = QGraphicsRectItem(min(ax, bx) - 0.5, min(ay, by) - 0.5, abs(bx - ax) + 1, abs(by - ay) + 1)
        else:
            item = QGraphicsLineItem(ax, ay, bx, by)
        pen = QPen(QColor("#ffd60a"))
        pen.setCosmetic(True)
        item.setPen(pen)
        self.scene().addItem(item)
        self._rubber = item

    def contextMenuEvent(self, event):
        if self.data is not None:
            x, y = self._array_xy(QPointF(event.pos()))
            self.context_requested.emit(x, y, event.globalPos())

    def mousePressEvent(self, event):
        self._press = event.position()
        if self.tool in ("area", "line") and self.data is not None and event.button() == Qt.LeftButton:
            self._drag_start = self._array_xy(event.position())
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_start is not None:
            x0, y0 = self._drag_start
            x1, y1 = self._array_xy(event.position())
            self._drag_start = None
            self._press = None
            self.show_selection(self.tool, x0, y0, x1, y1)
            if self.tool == "area":
                self.region_selected.emit(x0, y0, x1, y1)
            else:
                self.line_selected.emit(x0, y0, x1, y1)
            return
        super().mouseReleaseEvent(event)
        if self._pick:  # the hand drag put its own cursor back
            self.viewport().setCursor(Qt.CrossCursor)
        if self._press is not None and self.data is not None and event.button() == Qt.LeftButton:
            if (event.position() - self._press).manhattanLength() < 4:  # a click, not a pan
                p = self.mapToScene(event.position().toPoint())
                self.clicked.emit(p.x() - 0.5, self.data.shape[0] - 0.5 - p.y())
        self._press = None

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.data is None:
            return
        if self._drag_start is not None:  # rubber band while dragging
            self.show_selection(self.tool, *self._drag_start, *self._array_xy(event.position()))
        p: QPointF = self.mapToScene(event.position().toPoint())
        if self._pick and self._hover_rings and not event.buttons():
            self._draw_hover(p.x(), p.y())
        h, w = self.data.shape
        col, row_from_top = int(p.x()), int(p.y())
        if 0 <= col < w and 0 <= row_from_top < h:
            row = h - 1 - row_from_top
            self.hovered.emit(col + 1, row + 1, float(self.data[row, col]))
