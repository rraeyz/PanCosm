"""A scatter item whose points all share one style skips pyqtgraph's per-point atlas look-up (a Python loop over
every point, 0.4 s for 10^6 points on each pan) and gives them that style's atlas place at once (PER-W: 30 fps)."""

import numpy as np
import pyqtgraph as pg
from pyqtgraph.graphicsItems.ScatterPlotItem import _DEFAULT_STYLE

STYLE = ("symbol", "size", "pen", "brush")


class FastScatter(pg.ScatterPlotItem):
    def updateSpots(self, dataSet=None):  # noqa: N802 (pyqtgraph's name)
        data = self.data if dataSet is None else dataSet
        if not (self.opts["pxMode"] and self.opts["useCache"]) or self.opts["hoverable"] or len(data) == 0:
            return super().updateSpots(dataSet)
        todo = data["sourceRect"]["w"] == 0
        if not todo.any() or not all(np.equal(data[k][todo], _DEFAULT_STYLE[k]).all() for k in STYLE):
            return super().updateSpots(dataSet)  # a point with its own style: pyqtgraph's own way
        one = self.fragmentAtlas[[tuple(self.opts[k] for k in STYLE)]][0]
        data["sourceRect"][todo] = one
        self._maybeRebuildAtlas()
        self._updateMaxSpotSizes(data=data)
        self.invalidate()

    def setData(self, *args, **kargs):  # noqa: N802 (pyqtgraph's name)
        """x, y and data only (the view's redraw on each pan): the record array from np.zeros, as np.empty fills its
        object fields one by one (10 ms for 34 000 points); anything else is pyqtgraph's own way."""
        if len(args) != 2 or set(kargs) - {"data"}:
            return super().setData(*args, **kargs)
        self.clear()
        data = np.zeros(len(args[1]), dtype=self.data.dtype)
        for k in data.dtype.names:
            if data.dtype[k].hasobject:  # np.zeros puts 0 there; pyqtgraph reads None as "the item's own"
                data[k] = None
        data["x"], data["y"], data["size"], data["visible"] = args[0], args[1], -1, True
        self.data = data
        if "data" in kargs:
            self.setPointData(kargs["data"], dataSet=data)
        self.prepareGeometryChange()
        self.informViewBoundsChanged()
        self.bounds = [None, None]
        self.invalidate()
        self.updateSpots(data)
        self.sigPlotChanged.emit(self)
