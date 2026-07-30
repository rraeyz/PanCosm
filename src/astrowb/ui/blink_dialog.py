"""Blink a series of images (as MaxIm DL, AstroImageJ and DS9 do): the frames one after the other with the
same display levels, optionally aligned on the stars, so moving or changing objects catch the eye."""

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from .viewer import ImageViewer


class BlinkDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Blink images"))
        self.resize(1000, 760)
        self.paths, self.cache, self.offsets, self.index = [], {}, {}, 0
        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        choose = QPushButton(self.tr("Choose images…"), self)
        choose.clicked.connect(self._choose)
        row.addWidget(choose)
        self.align = QCheckBox(self.tr("Align on the stars"), self)
        self.align.setChecked(True)
        self.align.toggled.connect(lambda *_: self.show_frame(self.index))
        row.addWidget(self.align)
        row.addWidget(QLabel(self.tr("Interval (ms)"), self))
        self.interval = QSpinBox(self)
        self.interval.setRange(50, 10000)
        self.interval.setValue(500)
        self.interval.valueChanged.connect(lambda v: self.timer.setInterval(v))
        row.addWidget(self.interval)
        self.play = QPushButton(self.tr("Play"), self)
        self.play.setCheckable(True)
        self.play.toggled.connect(self._toggle)
        row.addWidget(self.play)
        for text, step in (("◀", -1), ("▶", 1)):
            b = QPushButton(text, self)
            b.clicked.connect(lambda _=False, s=step: self.show_frame(self.index + s))
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.viewer = ImageViewer(self)
        lay.addWidget(self.viewer, 1)
        self.slider = QSlider(Qt.Horizontal, self)
        self.slider.valueChanged.connect(self.show_frame)
        lay.addWidget(self.slider)
        self.label = QLabel(self.tr("Choose two or more images."), self)
        lay.addWidget(self.label)
        self.timer = QTimer(self)
        self.timer.setInterval(self.interval.value())
        self.timer.timeout.connect(lambda: self.show_frame(self.index + 1))

    def _choose(self):
        paths, _ = QFileDialog.getOpenFileNames(self, self.tr("Choose images"), "", "FITS (*.fits *.fit *.fts)")
        if len(paths) >= 2:
            self.set_images(paths)

    def set_images(self, paths):
        from .. import timing
        from ..display import display_limits

        self.paths, self.cache, self.offsets = timing.chronological(paths), {}, {}
        first = self._data(0)
        self.viewer.set_image(first)
        self.viewer.set_levels(display_limits(first))  # one stretch for every frame, so changes are real
        self.slider.blockSignals(True)
        self.slider.setRange(0, len(self.paths) - 1)
        self.slider.blockSignals(False)
        self.show_frame(0)

    def _data(self, i):
        if i not in self.cache:
            from ..io.fits import read_image

            if len(self.cache) > 64:  # shortcut: simple cache cap, enough for blinking a night's frames in turns
                self.cache.pop(next(iter(self.cache)))
            self.cache[i] = read_image(self.paths[i])[0]
        return self.cache[i]

    def frame(self, i):
        """Frame i, shifted onto the first frame (whole pixels) when aligning."""
        data = self._data(i)
        if not self.align.isChecked() or i == 0:
            return data
        if i not in self.offsets:
            from ..photometry.aperture import frame_shift

            ref = self._data(0)
            self.offsets[i] = frame_shift(ref, data) if data.shape == ref.shape else (0.0, 0.0)
        dx, dy = self.offsets[i]
        return np.roll(data, (-round(dy), -round(dx)), axis=(0, 1))

    def show_frame(self, i):
        if not self.paths:
            return
        self.index = i % len(self.paths)
        self.viewer.data = self.frame(self.index)
        self.viewer.refresh()
        self.slider.blockSignals(True)
        self.slider.setValue(self.index)
        self.slider.blockSignals(False)
        self.label.setText(f"{self.index + 1} / {len(self.paths)}  {Path(self.paths[self.index]).name}")

    def _toggle(self, on):
        self.play.setText(self.tr("Pause") if on else self.tr("Play"))
        self.timer.start() if on else self.timer.stop()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)
