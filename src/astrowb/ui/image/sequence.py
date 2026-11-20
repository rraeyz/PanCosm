"""A sequence of frames on one viewer (ARC-7 item 7): slider, previous / next, play (blink) at a chosen rate, the
neighbouring frames read ahead, and display levels fixed for the whole sequence or taken per frame."""

from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QCoreApplication, QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QHBoxLayout, QPushButton, QSlider, QWidget

translate = QCoreApplication.translate


def read_frame(path):
    """(data, wcs or None) of a FITS file."""
    from astropy.wcs import WCS

    from ...io.fits import read_image

    data, header, _ = read_image(path)
    wcs = WCS(header)
    return data, (wcs if wcs.has_celestial else None)


class Frames(QObject):
    """The frames of one sequence with a read-ahead cache of the frames either side of the current one."""

    def __init__(self, paths, loader=read_frame):
        super().__init__()
        self.paths, self.loader = list(paths), loader
        self._pool, self._cache = ThreadPoolExecutor(1), {}

    def get(self, i):
        data = self._cache.pop(i, None)
        frame = data.result() if data is not None else self.loader(self.paths[i])
        self._cache = {j: f for j, f in self._cache.items() if abs(j - i) == 1}
        for j in (i - 1, i + 1):
            if 0 <= j < len(self.paths) and j not in self._cache:
                self._cache[j] = self._pool.submit(self.loader, self.paths[j])
        return frame

    def close(self):
        """Stop the read-ahead thread (the bar calls it when it goes)."""
        self._pool.shutdown(wait=False, cancel_futures=True)


class SequenceBar(QWidget):
    frame_changed = Signal(int)

    def __init__(self, viewer, paths, loader=read_frame):
        super().__init__()
        self.viewer, self.frames, self.index = viewer, Frames(paths, loader), -1
        self.destroyed.connect(self.frames.close)  # no read-ahead thread outlives its bar
        self.slider = QSlider()
        self.slider.setOrientation(Qt.Horizontal)
        self.slider.setRange(0, max(len(paths) - 1, 0))
        prev, nxt = QPushButton("<"), QPushButton(">")
        self.play = QPushButton(translate("Sequence", "Play"))
        self.play.setCheckable(True)
        self.rate = QDoubleSpinBox()
        self.rate.setRange(0.2, 30)
        self.rate.setValue(2)
        self.rate.setSuffix(translate("Sequence", " frames/s"))
        self.same_levels = QCheckBox(translate("Sequence", "Same levels for all frames"))
        self.timer = QTimer(self)
        layout = QHBoxLayout(self)
        for w in (prev, self.slider, nxt, self.play, self.rate, self.same_levels):
            layout.addWidget(w)
        self.slider.valueChanged.connect(self.show_frame)
        prev.clicked.connect(lambda: self.step(-1))
        nxt.clicked.connect(lambda: self.step(1))
        self.play.toggled.connect(self._toggle)
        self.rate.valueChanged.connect(lambda: self.timer.setInterval(int(1000 / self.rate.value())))
        self.timer.timeout.connect(lambda: self.step(1, wrap=True))
        self.same_levels.toggled.connect(self._levels)
        if paths:
            self.show_frame(0)

    def step(self, d, wrap=False):
        n = len(self.frames.paths)
        i = self.index + d
        self.slider.setValue(i % n if wrap else min(max(i, 0), n - 1))

    def show_frame(self, i):
        data, wcs = self.frames.get(i)
        first = self.index < 0
        self.index = i
        self.viewer.set_image(data, keep_view=not first, wcs=wcs)
        if first and self.same_levels.isChecked():
            self._levels(True)
        self.frame_changed.emit(i)

    def _levels(self, fixed):
        """Fixed: the levels of the frame now shown stay for every frame; otherwise each frame sets its own."""
        from ...display import display_limits

        self.viewer.set_levels(limits=display_limits(self.viewer.data, self.viewer.interval) if fixed else None)

    def _toggle(self, on):
        self.timer.setInterval(int(1000 / self.rate.value()))
        self.timer.start() if on else self.timer.stop()
