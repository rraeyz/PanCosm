"""Live follow (PHO-19): refresh the result views at most once per interval, however fast frames arrive."""

import time

import numpy as np
from PySide6.QtCore import QCoreApplication, QObject, QTimer

translate = QCoreApplication.translate


class Throttled(QObject):
    """request() runs fn now, or, within ms of the last run, once when the interval ends (many calls, one run)."""

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


class StallWatch:
    """A night with no new frame for 3 x the usual cadence shows a banner (never an error); a new frame removes it.

    The cadence is the median gap between the frames' times (needs 3 frames); idle time is wall-clock, from clock()."""

    def __init__(self, layout, session, timer, clock=time.monotonic):
        self.layout, self.session, self.clock = layout, session, clock
        self.seen, self.last, self.banner = 0, clock(), None
        timer.timeout.connect(self.check)

    def clear(self):
        if self.banner is not None:
            self.banner.deleteLater()
            self.banner = None

    def check(self):
        n = len(self.session.jd)
        if n != self.seen:
            self.seen, self.last = n, self.clock()
        cadence = float(np.median(np.diff(sorted(self.session.jd.values())))) * 86400 if n >= 3 else 0
        idle = self.clock() - self.last
        if cadence <= 0 or idle < 3 * cadence:
            self.clear()
            return
        from .kit.banners import InfoBanner

        text = translate(
            "PhotometryPage",
            "No new frame for {minutes} min (about 3 \u00d7 the usual {cadence} s between frames). "
            "Still watching the folder.",
        ).format(minutes=round(idle / 60), cadence=round(cadence))
        if self.banner is None:
            self.banner = InfoBanner("attention", text)
            self.layout.addWidget(self.banner)
        else:
            self.banner.label.setText(text)


def start_timers(page):
    """The live run's throttle, its 3 s folder poll and the stall banner's watch."""
    page._live_throttle = Throttled(page, page._live_show)  # a fast folder must not freeze the views
    page.live_updated.connect(page._live_throttle.request)
    page._live_timer = QTimer(page)
    page._live_timer.timeout.connect(page.poll_live)
    page.stall = StallWatch(page.layout(), page.live, page._live_timer)  # the banner sits under the page
    page._live_timer.start(3000)
