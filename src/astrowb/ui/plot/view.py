"""PlotView: draws a FigureSpec with pyqtgraph, with the same mouse and keyboard in every window (ARC-6).

    wheel            zoom at the cursor (Ctrl: x only, Shift: y only)
    drag             pan                      right-drag or Z + drag   box zoom
    A / double-click show all                 R + drag                 select an x range  -> range_selected(x0, x1)
    X + click, click  measure: measured(dx, dy) between two clicks (also the toolbar's Measure)
    Delete            key_pressed("delete", x): a page's "leave out" of what it selected
    click a point    point_clicked(series, id) (pickable series)       L + drag   lasso -> points_selected(series, ids)
    legend entry     shows / hides its series  mouse move               cursor_moved(text) for the status bar

Series with more than spec.MAX_POINTS points in view are decimated on every view change (spec.decimate_*), so a
million points pan smoothly without OpenGL. Times are drawn minus a round offset written in the axis title.
"""

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QCoreApplication, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QGraphicsItem, QGraphicsPathItem, QLabel, QVBoxLayout, QWidget

from ..kit import tokens
from . import spec as S

translate = QCoreApplication.translate  # the texts of PlotCanvas ("PlotCanvas" context), so one translation serves both
PICK_PX = 6  # a click this near a point of a pickable series picks it
HELD = {Qt.Key_R: "range", Qt.Key_L: "lasso", Qt.Key_Z: "zoom", Qt.Key_X: "measure"}  # modes while their key is held
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
        if ev.button() == Qt.LeftButton and self.view.mode == "measure":
            ev.accept()
            self.view._measure(self, ev.scenePos())
            return
        if ev.button() == Qt.LeftButton and self.view._pick(self, ev.scenePos()):
            ev.accept()
            return
        if ev.button() == Qt.LeftButton:
            self.view._clicked(self, ev.scenePos())
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
                self._lasso_item.setPen(QPen(QColor(tokens.DARK["accent"]), 0))
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


def _cmap():
    return pg.colormap.get("viridis")


def _colours(values):
    """One colour per value along the colour map, from the smallest to the largest (NaN: the smallest)."""
    v = np.nan_to_num(np.asarray(values, float), nan=np.nanmin(values) if np.isfinite(values).any() else 0.0)
    span = np.ptp(v) or 1.0
    return _cmap().map((v - v.min()) / span, mode="qcolor")


class PlotView(QWidget):
    range_selected = Signal(float, float)
    point_clicked = Signal(str, object)
    points_selected = Signal(str, list)
    cursor_moved = Signal(str)
    measured = Signal(float, float)  # Δx, Δy between two clicks in "measure" mode (UI-10)
    plot_clicked = Signal(int, float, float)  # panel, x, y of a click that hit no pickable point
    key_pressed = Signal(str, object)  # a letter key the view does not use itself, and the cursor's x (None: outside)

    def __init__(self, figure=None, parent=None):
        super().__init__(parent)
        self.graphics = pg.GraphicsLayoutWidget()
        pal = self.palette()  # the theme's colours (ui/theme.py, from kit/tokens.py), dark or light
        self._ink, self._muted = pal.color(pal.ColorRole.Text), pal.color(pal.ColorRole.PlaceholderText)
        self.graphics.setBackground(pal.color(pal.ColorRole.Base))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.graphics)
        self.setFocusPolicy(Qt.StrongFocus)
        self.base_mode = "pan"  # what a released key goes back to; the toolbar sets it
        self.mode = "pan"  # "range", "lasso", "zoom" while their key is held, or set by the toolbar
        self.figure, self.plots, self.items, self.offsets = None, [], [], {}
        self.colourbars, self._pool = [], []
        self.cursor_x = None
        self._measure_from = None
        self.hit = None  # (series, id, x, y) nearest the cursor, for keys like Delete
        self.graphics.scene().sigMouseMoved.connect(self._mouse_moved)
        # said over the empty plot (UI-6: no blank rectangle without words), as PlotCanvas does
        self._empty_text = translate("PlotCanvas", "Nothing to show yet: the plot appears here once there are results")
        self.failed = None
        self.hint = QLabel(self._empty_text, self.graphics.viewport())
        self.hint.setWordWrap(True)
        self.hint.setAlignment(Qt.AlignCenter)
        self.hint.setProperty("muted", True)
        self.hint.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._update_hint()
        if figure is not None:
            self.set_figure(figure)

    # --- drawing ------------------------------------------------------------------
    def set_time_mode(self, mode):
        """Show time axes as "bjd", "ut" (hours of the night) or "phase" (when the axis has a period)."""
        self.set_figure(self.original, keep=True) if mode == "bjd" else self.set_figure(
            S.in_time_mode(self.original, mode), keep=True
        )

    def set_figure(self, figure, keep=False):
        """Draw the figure; a figure that cannot be drawn says why over the plot (and is logged)."""
        try:
            self._draw_figure(figure, keep)
        except Exception as e:  # noqa: BLE001 (any failure while drawing: the window must go on)
            import logging

            logging.getLogger(__name__).warning("plot not drawn: %s", e, exc_info=True)
            self.failed = str(e)
            self.hint.setText(translate("PlotCanvas", "This plot could not be drawn: {error}").format(error=e))
            self.hint.setGeometry(self.graphics.viewport().rect().adjusted(24, 24, -24, -24))
            self.hint.show()
            self.hint.raise_()
            return
        if self.failed:
            self.failed = None
            self.hint.setText(self._empty_text)
        self._update_hint()

    def set_empty_hint(self, text):
        self._empty_text = text
        self.hint.setText(text)
        self._update_hint()

    def set_busy(self, text):
        """UI-6's loading state: while the window's task runs, an empty plot says so (None: back to its hint)."""
        self.hint.setText(text or self._empty_text)

    def is_empty(self):
        return not any(len(s.x) for p in (self.figure.panels if self.figure else []) for s in p.series)

    def _update_hint(self):
        empty = self.is_empty()
        self.hint.setVisible(empty)
        if empty:
            self.hint.setGeometry(self.graphics.viewport().rect().adjusted(24, 24, -24, -24))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_hint()

    def copy_picture(self):
        QApplication.clipboard().setPixmap(self.graphics.grab())

    def copy_data(self):
        """Tab-separated axis, series, x, y: pastes into a spreadsheet. Returns the number of rows."""
        lines = ["axis\tseries\tx\ty"]
        for a, panel in enumerate(self.figure.panels if self.figure else [], 1):
            for s in panel.series:
                if s.y is not None and s.kind not in S.NO_LEGEND:
                    lines += [
                        f"{panel.y.title() or f'axis {a}'}\t{s.name}\t{x}\t{y}" for x, y in zip(s.x, s.y, strict=False)
                    ]
        QApplication.clipboard().setText("\n".join(lines))
        return len(lines) - 1

    def _draw_figure(self, figure, keep):
        if not keep:
            self.original = figure
        # PlotItems are never destroyed while the view lives (freeing pyqtgraph's PySide-owned menus corrupted the
        # heap); a redraw takes them from the pool, a new one is made only for more panels than ever before
        for item in [*self.plots, *self.colourbars]:
            self.graphics.removeItem(item)
        for plot in self.plots:
            plot.hide()
        self.figure, self.plots, self.items, self.offsets = figure, [], [], {}
        self.colourbars = []
        colours = figure.colours()
        for row, panel in enumerate(figure.panels):
            plot = self._pool_plot(row, figure.title if row == 0 else None)
            vb = plot.vb
            self.graphics.ci.layout.setRowStretchFactor(row, max(1, round(panel.height_ratio * 10)))
            xs = [s.x for s in panel.series if s.x is not None and s.kind not in ("hline",)]
            offset = S.time_offset(np.concatenate(xs) if xs else None, panel.x)
            self.offsets[id(vb)] = offset
            plot.setLabel("bottom", panel.x.title(offset))
            plot.setLabel("left", panel.y.title())
            for side in ("left", "bottom"):
                axis = plot.getAxis(side)
                axis.setPen(self._muted)
                axis.setTextPen(self._ink)
            plot.setLogMode(x=panel.x.scale == "log", y=panel.y.scale == "log")  # the pool's reset left it linear
            vb.invertX(panel.x.invert)
            vb.invertY(panel.y.invert)
            vb.setAspectLocked(panel.equal)
            for side, axis_spec, shift in (("bottom", panel.x, offset), ("left", panel.y, 0.0)):
                if axis_spec.ticks:
                    plot.getAxis(side).setTicks([[(v - shift, t) for v, t in axis_spec.ticks]])
            if panel.top:
                plot.showAxis("top")
                plot.setLabel("top", panel.top.title())
                top = plot.getAxis("top")
                top.setPen(self._muted)
                top.setTextPen(self._ink)
                top.setTicks([[(v - offset, t) for v, t in panel.top.ticks or []]])
            if panel.right:
                plot.showAxis("right")
                plot.setLabel("right", panel.right.title())
                plot.getAxis("right").setPen(self._muted)
                plot.getAxis("right").setTextPen(self._ink)
                plot.getAxis("right").setTicks([[(v, t) for v, t in panel.right.ticks or []]])
            plot.showGrid(x=panel.grid, y=panel.grid, alpha=0.3)
            self._add_colourbar(row, panel)
            legend = plot.addLegend() if sum(s.kind not in S.NO_LEGEND for s in panel.series) > 1 else None
            for s in panel.series:
                self.items.append(self._add_series(plot, vb, s, colours[s.name], offset, legend))
            vb.disableAutoRange()  # its items hold only the decimated points in view: show_all() uses all the data
            if figure.shared_x and self.plots:
                plot.setXLink(self.plots[0])
            vb.sigRangeChanged.connect(vb.redraw_slot)
            vb.redraw_connected = True
            self.plots.append(plot)
        self.show_all()

    def _pool_plot(self, row, title):
        """The pooled PlotItem of this row, reset to what a new one is, and placed in the layout."""
        if row == len(self._pool):
            vb = _ViewBox(self)
            vb.redraw_connected = False
            vb.redraw_slot = lambda *_, vb=vb: self._redraw(vb)
            plot = pg.PlotItem(viewBox=vb)
            vb.menu.addSeparator()  # beside pyqtgraph's own entries: the same two as every PlotCanvas
            vb.menu.addAction(translate("PlotCanvas", "Copy picture"), self.copy_picture)
            vb.menu.addAction(translate("PlotCanvas", "Copy data"), self.copy_data)
            self._pool.append(plot)
        plot = self._pool[row]
        vb = plot.vb
        if vb.redraw_connected:
            vb.sigRangeChanged.disconnect(vb.redraw_slot)
            vb.redraw_connected = False
        plot.clear()
        if plot.legend is not None:
            QGraphicsItem.setParentItem(plot.legend, None)  # LegendItem's own override wants a parent
            plot.legend = None
        plot.setXLink(None)
        plot.setLogMode(False, False)
        for side in ("left", "bottom", "top", "right"):
            axis = plot.getAxis(side)
            axis.setTicks(None)
            axis.showLabel(False)
        plot.hideAxis("top")
        plot.hideAxis("right")
        plot.setTitle(title)
        plot.show()
        self.graphics.addItem(plot, row=row, col=0)
        return plot

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
            if s.kind == "span":
                xs += [e["x"][e["ok"]], s.y[e["ok"]] - off]
                continue
            xs.append(e["x"][e["ok"]])
            if s.kind == "histogram":  # n + 1 edges against n counts: the edges' mask does not fit the counts
                ys += [s.y[np.isfinite(s.y)], np.zeros(1)]
            elif s.y is not None and s.kind != "vline":
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

    def _add_colourbar(self, row, panel):
        values = [s.values for s in panel.series if s.values is not None and s.kind == "points"]
        values = np.concatenate(values) if values else np.array([])
        values = values[np.isfinite(values)]
        if not panel.colourbar or not len(values):
            return
        bar = pg.ColorBarItem(values=(values.min(), values.max()), colorMap=_cmap(), interactive=False)
        bar.axis.setLabel(panel.colourbar)  # on the side of the numbers (the item's own label goes to the other side)
        bar.axis.setPen(self._muted)
        bar.axis.setTextPen(self._ink)
        self.graphics.addItem(bar, row=row, col=1)
        self.colourbars.append(bar)

    def _add_series(self, plot, vb, s, colour, offset, legend):
        x = s.x - offset if s.kind != "hline" else s.x
        y = s.y
        ok = np.isfinite(x) & np.isfinite(y) if y is not None and s.kind not in ("histogram",) else np.isfinite(x)
        ids = s.ids if s.ids is not None else np.arange(len(s.x))
        colour = pg.mkColor(colour)
        colour.setAlphaF(s.alpha)
        dash = {"dash": Qt.DashLine, "dot": Qt.DotLine}.get(s.dash, Qt.SolidLine)
        pen, brush = pg.mkPen(colour, width=s.width, style=dash), pg.mkBrush(colour)
        entry = {"spec": s, "vb": vb, "x": x, "y": y, "ids": ids, "ok": ok, "errors": None, "brushes": None}
        if s.values is not None and s.kind == "points":
            entry["brushes"] = np.array([pg.mkBrush(c) for c in _colours(s.values)], dtype=object)
        if s.kind == "points" or s.kind == "errorbars":
            entry["item"] = pg.ScatterPlotItem(pen=None, brush=brush, size=s.size, symbol=_SYMBOLS.get(s.symbol, "o"))
            entry["item"].sigClicked.connect(lambda _i, _pts, ev, vb=vb: self._pick(vb, ev.scenePos()))  # on a dot
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
        elif s.kind == "span":  # shaded x ranges over the panel's whole height
            entry["item"] = pg.ItemGroup()
            entry["lines"] = [
                pg.LinearRegionItem((a, b - offset), movable=False, brush=brush, pen=pg.mkPen(None))
                for a, b in zip(x[ok], s.y[ok], strict=True)
            ]
            for region in entry["lines"]:
                plot.addItem(region, ignoreBounds=True)
        elif s.kind == "text":  # one label per point, at an angle
            entry["item"] = pg.ItemGroup()
            entry["lines"] = []
            for xi, yi, text in zip(x, y, s.labels or [], strict=False):
                if np.isfinite(xi) and np.isfinite(yi):
                    label = pg.TextItem(text, color=colour, anchor=(0.5, 0.0), angle=-s.angle)
                    label.setPos(xi, yi)
                    entry["lines"].append(label)
                    plot.addItem(label, ignoreBounds=True)
        else:  # vline, hline: one infinite line per value
            angle = 90 if s.kind == "vline" else 0
            entry["item"] = pg.ItemGroup()
            entry["lines"] = [
                pg.InfiniteLine(self._line_pos(vb, v, s.kind == "vline"), angle=angle, pen=pen)
                for v in (x if s.kind == "vline" else s.x)
            ]
            for line in entry["lines"]:
                plot.addItem(line)
        entry["item"].setZValue(s.z)
        plot.addItem(entry["item"])
        if (
            legend is not None and s.kind not in S.NO_LEGEND and not any(e["spec"].name == s.name for e in self.items)
        ):  # series sharing a name (pieces of one curve) get one legend entry
            legend.addItem(entry["item"], s.name)
        entry["item"].setVisible(s.visible)
        return entry

    @staticmethod
    def _line_pos(vb, value, vertical):
        """Where an infinite line sits: pyqtgraph does not log-map lines on a log axis."""
        return np.log10(max(value, 1e-300)) if vb.state["logMode"][0 if vertical else 1] else value

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
            if e["vb"] is not vb or e["spec"].kind in ("band", "vline", "hline", "histogram", "text", "span"):
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
            lx, ly = (
                np.log10(np.clip(v, 1e-300, None)) if m else v
                for v, m in zip((x[index], y[index]), vb.state["logMode"], strict=True)
            )
            brush = {} if e["brushes"] is None else {"brush": list(e["brushes"][index])}
            e["item"].setData(lx, ly, data=e["ids"][index], **brush)  # a scatter item has no log mode of its own
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
                ring = e["ring"] = pg.ScatterPlotItem(pen=pg.mkPen(tokens.DARK["accent"], width=2), brush=None, size=11)
                ring.setZValue(e["spec"].z + 100)
                e["vb"].addItem(ring)
            index = np.flatnonzero(np.isin(e["ids"], np.asarray(ids)) & e["ok"])
            ring.setData(e["x"][index], e["y"][index])

    def move_vline(self, name, value):
        """Put the vline series `name` at `value` without redrawing the figure (a draggable level)."""
        for e in self.items:
            if e["spec"].name == name and e["spec"].kind == "vline":
                e["spec"].x = np.array([value])
                for line in e["lines"]:
                    line.setValue(self._line_pos(e["vb"], value - self.offsets[id(e["vb"])], True))

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
        elif key in HELD and not ev.isAutoRepeat():
            self.mode = HELD[key]
        elif key == Qt.Key_Delete:
            self.key_pressed.emit("delete", self.cursor_x)
        elif ev.text().isalpha() and not ev.isAutoRepeat():
            self.key_pressed.emit(ev.text().lower(), self.cursor_x)
        else:
            super().keyPressEvent(ev)

    def keyReleaseEvent(self, ev):
        if ev.key() in HELD and not ev.isAutoRepeat():
            self.mode = self.base_mode
            self._measure_from = None
        else:
            super().keyReleaseEvent(ev)

    def _pick(self, vb, pos, tol=PICK_PX):
        """Emit point_clicked for the pickable point nearest to the scene position `pos` within `tol` px;
        screen distance, so log axes and zoom behave. True when a point was hit."""
        tr, best = vb.childGroup.sceneTransform(), None  # child (log-mapped data) to scene px
        for e in self.items:
            index = e.get("shown")
            if (
                e["vb"] is not vb
                or not e["spec"].pickable
                or index is None
                or not len(index)
                or not e["item"].isVisible()
            ):
                continue
            lx, ly = (
                np.log10(np.clip(v[index], 1e-300, None)) if m else v[index]
                for v, m in zip((e["x"], e["y"]), vb.state["logMode"], strict=True)
            )
            px = tr.m11() * lx + tr.m21() * ly + tr.dx()
            py = tr.m12() * lx + tr.m22() * ly + tr.dy()
            d = np.hypot(px - pos.x(), py - pos.y())
            k = int(np.argmin(d))
            if d[k] <= tol and (best is None or d[k] < best[0]):
                best = (d[k], e["spec"].name, _plain(e["ids"][index[k]]))
        if best:
            self.point_clicked.emit(best[1], best[2])
        return best is not None

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

    def _clicked(self, vb, pos):
        p = vb.mapSceneToView(pos)
        x, y = (10**v if m else v for v, m in zip((p.x(), p.y()), vb.state["logMode"], strict=True))
        panel = next(i for i, plot in enumerate(self.plots) if plot.getViewBox() is vb)
        self.plot_clicked.emit(panel, x + self.offsets.get(id(vb), 0.0), y)

    def _measure(self, vb, pos):
        """The first click sets the start, the second reports the difference (x in the axis' own units, y as drawn)."""
        p = vb.mapSceneToView(pos)
        here = (p.x(), p.y())
        if self._measure_from is None:
            self._measure_from = here
            return
        dx, dy = here[0] - self._measure_from[0], here[1] - self._measure_from[1]
        self._measure_from = None
        self.measured.emit(dx, dy)
        self.cursor_moved.emit(translate("PlotCanvas", "Δx = {dx:.6g}   Δy = {dy:.6g}").format(dx=dx, dy=dy))

    def _mouse_moved(self, pos):
        self.cursor_x = self.hit = None
        for plot in self.plots:
            vb = plot.getViewBox()
            if vb.sceneBoundingRect().contains(pos):
                p = vb.mapSceneToView(pos)
                off = self.offsets.get(id(vb), 0.0)
                self.cursor_x = p.x() + off
                text = f"x = {p.x() + off:.6g}   y = {p.y():.6g}"
                hit = self.hit = self.nearest(vb, p.x(), p.y())
                if hit is not None:
                    text += f"   {hit[0]} #{hit[1]}"
                self.cursor_moved.emit(text)
                return


def _plain(value):
    return value.item() if hasattr(value, "item") else value
