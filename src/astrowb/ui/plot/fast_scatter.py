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
