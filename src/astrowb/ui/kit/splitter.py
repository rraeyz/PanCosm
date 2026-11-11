"""Resizable panes of the component kit (plans/interface.md "The component kit", UI-3): the sizes are remembered per
window, and a double-click on a handle puts the first sizes back.

    split = Splitter(Qt.Horizontal, settings, "photometry.main")
    split.addWidget(left); split.addWidget(right); split.setSizes([300, 900])
    split.restore()                         # after the panes are in: the sizes the user left last time
"""

from PySide6.QtWidgets import QSplitter, QSplitterHandle


class _Handle(QSplitterHandle):
    def mouseDoubleClickEvent(self, event):
        self.splitter().reset()


class Splitter(QSplitter):
    def __init__(self, orientation, settings=None, key=None, parent=None):
        super().__init__(orientation, parent)
        self.settings, self.key, self._first = settings, key, None
        self.setChildrenCollapsible(False)
        self.splitterMoved.connect(lambda *_: self._save())

    def createHandle(self):
        return _Handle(self.orientation(), self)

    def restore(self):
        """Remember the sizes set so far as the first ones, then show the stored sizes when they fit the panes."""
        self._first = self.sizes()
        stored = self.settings.get(f"split.{self.key}") if self.settings is not None and self.key else None
        if isinstance(stored, list) and len(stored) == self.count() and all(isinstance(v, int) for v in stored):
            self.setSizes(stored)

    def reset(self):
        if self._first:
            self.setSizes(self._first)
            self._save()

    def _save(self):
        if self.settings is not None and self.key:
            self.settings.set(f"split.{self.key}", self.sizes())
