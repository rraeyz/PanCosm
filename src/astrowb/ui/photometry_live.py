"""Live follow (PHO-19): refresh the result views at most once per interval, however fast frames arrive."""

from PySide6.QtCore import QObject, QTimer


class Throttled(QObject):
    """request() runs fn now, or, within ms of the last run, once when the interval ends (many requests, one run)."""

    def __init__(self, parent, fn, ms=500):
        super().__init__(parent)
        self.fn, self.pending = fn, False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(ms)
        self.timer.timeout.connect(self._end)

    def request(self):
        if self.timer.isActive():
            self.pending = True
            return
        self.fn()
        self.timer.start()

    def _end(self):
        if self.pending:
            self.pending = False
            self.request()
