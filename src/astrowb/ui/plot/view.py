"""PlotView: draws a FigureSpec with pyqtgraph, with the same mouse and keyboard in every window (ARC-6).

    wheel            zoom at the cursor (Ctrl: x only, Shift: y only)
    drag             pan                      right-drag or Z + drag   box zoom
    A / double-click show all                 R + drag                 select an x range  -> range_selected(x0, x1)
    click a point    point_clicked(series, id) (pickable series)       L + drag   lasso -> points_selected(series, ids)
    legend entry     shows / hides its series  mouse move               cursor_moved(text) for the status bar

Series with more than spec.MAX_POINTS points in view are decimated on every view change (spec.decimate_*), so a
million points pan smoothly without OpenGL. Times are drawn minus a round offset written in the axis title.
"""

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsPathItem, QVBoxLayout, QWidget

from . import spec as S

_SYMBOLS = {"o": "o", "s": "s", "^": "t1", "v": "t", "d": "d", "+": "+", "x": "x", "*": "star"}


class _ViewBox(pg.ViewBox):
    """A ViewBox that knows the view's modes (range selection, lasso, box zoom) and the wheel modifiers."""

    def __init__(self, view):
        super().__init__()
        self.view = view
        self._region = None
        self._lasso = None

    def wheelEvent(self, ev, axis=None):
        mods = ev.modifiers()
        if mods & Qt.ControlModifier:
            axis = 0
        elif mods & Qt.ShiftModifier:
            axis = 1
        super().wheelEvent(ev, axis)

    def mouseClickEvent(self, ev):
        if ev.button() == Qt.LeftButton and ev.double():
            ev.accept()
            self.view.show_all()
            return
        super().mouseClickEvent(ev)

    def mouseDragEvent(self, ev, axis=None):
        mode = self.view.mode
        if ev.button() == Qt.RightButton or (mode == "zoom" and ev.button() == Qt.LeftButton):
            self.setMouseMode(pg.ViewBox.RectMode)
            ev = _AsLeft(ev)
            super().mouseDragEvent(ev, axis)
            self.setMouseMode(pg.ViewBox.PanMode)
            return
        if mode == "range" and ev.button() == Qt.LeftButton:
            ev.accept()
            x0, x1 = sorted((self.mapSceneToView(ev.buttonDownScenePos()).x(), self.mapSceneToView(ev.scenePos()).x()))
            if self._region is None:
                self._region = pg.LinearRegionItem(movable=False, brush=pg.mkBrush(0, 114, 178, 50))
                self.addItem(self._region, ignoreBounds=True)
            self._region.setRegion((x0, x1))
            if ev.isFinish():
                off = self.view.offsets.get(id(self), 0.0)
                self.view.range_selected.emit(x0 + off, x1 + off)
            return
        if mode == "lasso" and ev.button() == Qt.LeftButton:
            ev.accept()
            p = self.mapSceneToView(ev.scenePos())
            if ev.isStart() or self._lasso is None:
                self._lasso = QPainterPath(self.mapSceneToView(ev.buttonDownScenePos()))
                self._lasso_item = QGraphicsPathItem()
                self._lasso_item.setPen(QPen(QColor("#D55E00"), 0))
                self.addItem(self._lasso_item, ignoreBounds=True)
            self._lasso.lineTo(p)
            self._lasso_item.setPath(self._lasso)
            if ev.isFinish():
                self._lasso.closeSubpath()
                self.view._lasso_done(self, self._lasso)
                self.removeItem(self._lasso_item)
                self._lasso = None
            return
        super().mouseDragEvent(ev, axis)

    def clear_region(self):
        if self._region is not None:
            self.removeItem(self._region)
            self._region = None


class _AsLeft:
    """A drag event that reports the left button, so that pyqtgraph's box zoom also runs on a right drag."""

    def __init__(self, ev):
        self._ev = ev

    def __getattr__(self, name):
        return getattr(self._ev, name)

    def button(self):
        return Qt.LeftButton

    def buttons(self):
        return Qt.LeftButton


class PlotView(QWidget):
    range_selected = Signal(float, float)
    point_clicked = Signal(str, object)
    points_selected = Signal(str, list)
    cursor_moved = Signal(str)

    def __init__(self, figure=None, parent=None):
        super().__init__(parent)
        self.graphics = pg.GraphicsLayoutWidget()
        self.graphics.setBackground("w")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.graphics)
        self.setFocusPolicy(Qt.StrongFocus)
        self.mode = "pan"  # "range", "lasso", "zoom" while their key is held, or set by the toolbar
        self.figure, self.plots, self.items, self.offsets = None, [], [], {}
        self.graphics.scene().sigMouseMoved.connect(self._mouse_moved)
        if figure is not None:
            self.set_figure(figure)

    # --- drawing ------------------------------------------------------------------
    def set_time_mode(self, mode):
        """Show time axes as "bjd", "ut" (hours of the night) or "phase" (when the axis has a period)."""
        self.set_figure(self.original, keep=True) if mode == "bjd" else self.set_figure(
            S.in_time_mode(self.original, mode), keep=True
        )

    def set_figure(self, figure, keep=False):
        if not keep:
            self.original = figure
        self.graphics.clear()
        self.figure, self.plots, self.items, self.offsets = figure, [], [], {}
        colours = figure.colours()
        for row, panel in enumerate(figure.panels):
            vb = _ViewBox(self)
            plot = self.graphics.addPlot(row=row, col=0, viewBox=vb, title=figure.title if row == 0 else None)
            self.graphics.ci.layout.setRowStretchFactor(row, max(1, round(panel.height_ratio * 10)))
            xs = [s.x for s in panel.series if s.x is not None and s.kind not in ("hline",)]
            offset = S.time_offset(np.concatenate(xs) if xs else None, panel.x)
            self.offsets[id(vb)] = offset
            plot.setLabel("bottom", panel.x.title(offset))
            plot.setLabel("left", panel.y.title())
            plot.setLogMode(x=panel.x.scale == "log", y=panel.y.scale == "log")
            vb.invertX(panel.x.invert)
            vb.invertY(panel.y.invert)
            plot.showGrid(x=panel.grid, y=panel.grid, alpha=0.3)
            legend = plot.addLegend() if len(panel.series) > 1 else None
            for s in panel.series:
                self.items.append(self._add_series(plot, vb, s, colours[s.name], offset, legend))
            vb.disableAutoRange()  # its items hold only the decimated points in view: show_all() uses all the data
            if figure.shared_x and self.plots:
                plot.setXLink(self.plots[0])
            vb.sigRangeChanged.connect(lambda *_, vb=vb: self._redraw(vb))
            self.plots.append(plot)
        self.show_all()

    def _full_range(self, vb, panel):
        """((x0, x1), (y0, y1)) of all the data of a panel, or its limits when the spec gives them."""
        off = self.offsets[id(vb)]
        xs, ys = [], []
        for e in self.items:
            s = e["spec"]
            if e["vb"] is not vb or not e["item"].isVisible():
                continue
            if s.kind == "hline":
                ys.append(s.x)
                continue
            xs.append(e["x"][e["ok"]])
            if s.y is not None and s.kind != "vline":
                y, err = s.y[e["ok"]], (s.yerr[e["ok"]] if s.yerr is not None else 0)
                ys += [y - err, y + err]
        span = [np.nanmin(np.concatenate(v)) if v else 0.0 for v in (xs, ys)]
        top = [np.nanmax(np.concatenate(v)) if v else 1.0 for v in (xs, ys)]
        xr = (panel.x.limits[0] - off, panel.x.limits[1] - off) if panel.x.limits else (span[0], top[0])
        yr = panel.y.limits or (span[1], top[1])
        return xr, yr

    def show_all(self):
        """Every point of every visible series (or the spec's limits) in view."""
        for plot, panel in zip(self.plots, self.figure.panels if self.figure else [], strict=False):
            vb = plot.getViewBox()
            vb.clear_region()
            (x0, x1), (y0, y1) = self._full_range(vb, panel)
            if vb.state["logMode"][0]:
                x0, x1 = np.log10(max(x0, 1e-300)), np.log10(max(x1, 1e-300))
            if vb.state["logMode"][1]:
                y0, y1 = np.log10(max(y0, 1e-300)), np.log10(max(y1, 1e-300))
            vb.setRange(xRange=(x0, x1), yRange=(y0, y1), padding=None if not panel.x.limits else 0)
            self._redraw(vb)

    def _add_series(self, plot, vb, s, colour, offset, legend):
        x = s.x - offset if s.kind != "hline" else s.x
        y = s.y
        ok = np.isfinite(x) & np.isfinite(y) if y is not None and s.kind not in ("histogram",) else np.isfinite(x)
        ids = s.ids if s.ids is not None else np.arange(len(s.x))
        colour = pg.mkColor(colour)
        colour.setAlphaF(s.alpha)
        pen, brush = pg.mkPen(colour, width=s.width), pg.mkBrush(colour)
        entry = {"spec": s, "vb": vb, "x": x, "y": y, "ids": ids, "ok": ok, "errors": None}
        if s.kind == "points" or s.kind == "errorbars":
            entry["item"] = pg.ScatterPlotItem(pen=None, brush=brush, size=s.size, symbol=_SYMBOLS.get(s.symbol, "o"))
            entry["item"].sigClicked.connect(lambda _i, pts, ev, name=s.name: self._clicked(name, pts, ev))
            if s.yerr is not None or s.xerr is not None:
                entry["errors"] = pg.ErrorBarItem(pen=pen)
                plot.addItem(entry["errors"])
        elif s.kind in ("line", "steps"):
            entry["item"] = pg.PlotDataItem(pen=pen, stepMode="left" if s.kind == "steps" else None)
        elif s.kind == "histogram":
            entry["item"] = pg.PlotDataItem(s.x, s.y, pen=pen, stepMode="center", fillLevel=0, brush=pg.mkBrush(colour))
        elif s.kind == "band":
            lo, hi = pg.PlotDataItem(x[ok], (y - s.yerr)[ok]), pg.PlotDataItem(x[ok], (y + s.yerr)[ok])
            band = pg.mkColor(colour)
            band.setAlphaF(0.25 * s.alpha)
            entry["item"] = pg.FillBetweenItem(lo, hi, brush=pg.mkBrush(band))
        else:  # vline, hline: one infinite line per value
            angle = 90 if s.kind == "vline" else 0
            entry["item"] = pg.ItemGroup()
            entry["lines"] = [pg.InfiniteLine(v, angle=angle, pen=pen) for v in (x if s.kind == "vline" else s.x)]
            for line in entry["lines"]:
                plot.addItem(line)
        entry["item"].setZValue(s.z)
        plot.addItem(entry["item"])
        if legend is not None and s.kind not in ("vline", "hline"):
            legend.addItem(entry["item"], s.name)
        entry["item"].setVisible(s.visible)
        return entry

    def _view_rect(self, vb):
        (x0, x1), (y0, y1) = vb.viewRange()
        if vb.state["logMode"][0]:
            x0, x1 = 10**x0, 10**x1
        if vb.state["logMode"][1]:
            y0, y1 = 10**y0, 10**y1
        return x0, x1, y0, y1

    def _redraw(self, vb):
        """Put the visible (decimated) points of every series of this panel into its items."""
        x0, x1, y0, y1 = self._view_rect(vb)
        width, height = max(int(vb.width()), 100), max(int(vb.height()), 100)
        for e in self.items:
            if e["vb"] is not vb or e["spec"].kind in ("band", "vline", "hline", "histogram"):
                continue
            s, x, y, ok = e["spec"], e["x"], e["y"], e["ok"]
            if s.kind in ("line", "steps"):
                xs, ys = x[ok], y[ok]
                if len(xs) > 1 and np.any(np.diff(xs) < 0):
                    order = np.argsort(xs, kind="stable")
                    xs, ys = xs[order], ys[order]
                e["item"].setData(*S.decimate_line(xs, ys, x0, x1, width))
                continue
            if not np.isfinite([x0, x1, y0, y1]).all() or (x0 == x1):  # nothing laid out yet: everything
                index = np.flatnonzero(ok)
            else:
                index = np.flatnonzero(ok)[S.decimate_points(x[ok], y[ok], x0, x1, y0, y1, width, height)]
            e["shown"] = index
            e["item"].setData(x[index], y[index], data=e["ids"][index])
            if e["errors"] is not None:
                small = len(index) <= S.MAX_ERRORBARS
                err = {}
                if s.yerr is not None:
                    err["height"] = 2 * s.yerr[index]
                if s.xerr is not None:
                    err["width"] = 2 * s.xerr[index]
                e["errors"].setData(x=x[index], y=y[index], **err) if small else e["errors"].setData(x=[], y=[])
                e["errors"].setVisible(small and e["item"].isVisible())

    def highlight(self, name, ids):
        """Ring the points of series `name` whose ids are given (a selection in a linked table); [] clears."""
        for e in self.items:
            if e["spec"].name != name or e["y"] is None:
                continue
            ring = e.get("ring")
            if ring is None:
                ring = e["ring"] = pg.ScatterPlotItem(pen=pg.mkPen("#D55E00", width=2), brush=None, size=11)
                ring.setZValue(e["spec"].z + 100)
                e["vb"].addItem(ring)
            index = np.flatnonzero(np.isin(e["ids"], np.asarray(ids)) & e["ok"])
            ring.setData(e["x"][index], e["y"][index])

    def set_visible(self, name, visible):
        for e in self.items:
            if e["spec"].name == name:
                e["item"].setVisible(visible)
                for line in e.get("lines", []):
                    line.setVisible(visible)
                if e["errors"] is not None:
                    e["errors"].setVisible(visible)

    # --- interaction ------------------------------------------------------------------
    def keyPressEvent(self, ev):
        key = ev.key()
        if key == Qt.Key_A:
            self.show_all()
        elif key in (Qt.Key_R, Qt.Key_L, Qt.Key_Z) and not ev.isAutoRepeat():
            self.mode = {Qt.Key_R: "range", Qt.Key_L: "lasso", Qt.Key_Z: "zoom"}[key]
        else:
            super().keyPressEvent(ev)

    def keyReleaseEvent(self, ev):
        if ev.key() in (Qt.Key_R, Qt.Key_L, Qt.Key_Z) and not ev.isAutoRepeat():
            self.mode = "pan"
        else:
            super().keyReleaseEvent(ev)

    def _clicked(self, name, points, ev):
        """Symbols overlap in dense data: report the one nearest to the click, not the topmost."""
        for e in self.items:
            if e["spec"].name == name and e["spec"].pickable and len(points):
                vb, p = e["vb"], ev.pos()
                x0, x1, y0, y1 = self._view_rect(vb)
                sx, sy = vb.width() / ((x1 - x0) or 1), vb.height() / ((y1 - y0) or 1)
                best = min(points, key=lambda q: ((q.pos().x() - p.x()) * sx) ** 2 + ((q.pos().y() - p.y()) * sy) ** 2)
                self.point_clicked.emit(name, _plain(best.data()))
                return

    def _lasso_done(self, vb, path):
        for e in self.items:
            if e["vb"] is vb and e["spec"].pickable and e["y"] is not None:
                s, ok = e["spec"], np.flatnonzero(e["ok"])
                inside = [i for i in ok if path.contains(QPointF(e["x"][i], e["y"][i]))]
                self.points_selected.emit(s.name, [_plain(e["ids"][i]) for i in inside])

    def nearest(self, vb, x, y):
        """(series name, id, x, y) of the shown point nearest to (x, y) in screen distance, or None."""
        best, (x0, x1, y0, y1) = None, self._view_rect(vb)
        sx, sy = vb.width() / ((x1 - x0) or 1), vb.height() / ((y1 - y0) or 1)
        for e in self.items:
            index = e.get("shown")
            if e["vb"] is not vb or index is None or not len(index) or not e["item"].isVisible():
                continue
            d = np.hypot((e["x"][index] - x) * sx, (e["y"][index] - y) * sy)
            k = int(np.argmin(d))
            if best is None or d[k] < best[0]:
                i = index[k]
                best = (d[k], e["spec"].name, _plain(e["ids"][i]), e["x"][i], e["y"][i])
        return None if best is None or best[0] > 20 else best[1:]

    def _mouse_moved(self, pos):
        for plot in self.plots:
            vb = plot.getViewBox()
            if vb.sceneBoundingRect().contains(pos):
                p = vb.mapSceneToView(pos)
                off = self.offsets.get(id(vb), 0.0)
                text = f"x = {p.x() + off:.6g}   y = {p.y():.6g}"
                hit = self.nearest(vb, p.x(), p.y())
                if hit is not None:
                    text += f"   {hit[0]} #{hit[1]}"
                self.cursor_moved.emit(text)
                return


def _plain(value):
    return value.item() if hasattr(value, "item") else value
