"""The Calibration window's frame preview (Check stage: image and histogram of the clicked frame) and the before /
after blink of one light (Review stage: the raw frame and its calibrated file, shown in turn)."""

import re
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .messages import translate as message

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("CalibrationWindow", "…") calls


def _stem(path):
    return re.sub(r"\.(fits?|fts)(\.gz|\.fz)?$", "", Path(path).name, flags=re.I)


class FramePreview(QWidget):
    """An image view, with a histogram of the same frame when `histogram` is set; read when asked for, not before."""

    def __init__(self, histogram=True, parent=None):
        super().__init__(parent)
        from .viewer import ImageViewer

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.viewer = ImageViewer(self)
        self.viewer.setMinimumHeight(140)
        lay.addWidget(self.viewer, 1)
        self.graph = None
        if histogram:
            from .plot.toolbar import plot_box

            box, self.graph = plot_box(self)
            box.setMinimumHeight(120)
            lay.addWidget(box, 1)

    def show_path(self, path):
        """Show the frame at `path`; raises OSError / ValueError when it cannot be read (the caller says it)."""
        from ..display import display_limits
        from ..io.fits import read_image

        data = read_image(path)[0]
        self.viewer.set_image(data)
        self.viewer.set_levels(display_limits(data))
        if self.graph is not None:
            from ..io.inspect import histogram
            from . import image_figures

            labels = (translate("CalibrationWindow", "Counts"), translate("CalibrationWindow", "Number of pixels"))
            self.graph.set_figure(image_figures.histogram_figure(histogram(data, bins=200, clip=(0.1, 99.9)), labels))

    def clear(self):
        self.viewer.clear()


class BeforeAfter(QWidget):
    """One light, raw and calibrated: Raw / Calibrated buttons and Blink, which swaps them every half second."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pair = None  # (raw path, calibrated path)
        self.shown = 0
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self.raw_button = QPushButton(translate("CalibrationWindow", "Raw"))
        self.calibrated_button = QPushButton(translate("CalibrationWindow", "Calibrated"))
        self.blink_button = QPushButton(translate("CalibrationWindow", "Blink"))
        self.blink_button.setCheckable(True)
        self.blink_button.setToolTip(translate("CalibrationWindow", "Shows the raw and the calibrated frame in turn"))
        for b in (self.raw_button, self.calibrated_button, self.blink_button):
            row.addWidget(b)
        row.addStretch(1)
        lay.addLayout(row)
        self.preview = FramePreview(histogram=False)
        lay.addWidget(self.preview, 1)
        self.status = QLabel()  # which frame is shown, or why none is
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(lambda: self.show_index(1 - self.shown))
        self.raw_button.clicked.connect(lambda: self.show_index(0))
        self.calibrated_button.clicked.connect(lambda: self.show_index(1))
        self.blink_button.toggled.connect(lambda on: self.timer.start() if on else self.timer.stop())
        self.set_pair(None)

    def set_pair(self, pair):
        self.pair = pair
        for b in (self.raw_button, self.calibrated_button, self.blink_button):
            b.setEnabled(pair is not None)
        if pair is None:
            self.blink_button.setChecked(False)
            self.preview.clear()
            self.status.setText(translate("CalibrationWindow", "Calibrate to blink a light before and after."))
        else:
            self.show_index(1)

    def show_index(self, i):
        if self.pair is None:
            return
        self.shown = i
        try:
            self.preview.show_path(self.pair[i])
        except (OSError, ValueError) as e:
            self.blink_button.setChecked(False)
            self.status.setText(message(e))
            return
        name = Path(self.pair[i]).name
        self.status.setText(
            (
                translate("CalibrationWindow", "Calibrated: {name}")
                if i
                else translate("CalibrationWindow", "Raw: {name}")
            ).format(name=name)
        )


def pair_of(frames, calibrated):
    """(raw path, calibrated path) of the first calibrated file whose raw light is in `frames` (a calibrated file
    is named after its light), or None."""
    raw = {_stem(f["path"]): f["path"] for f in frames if f["kind"] == "light"}
    return next(((raw[_stem(c)], c) for c in calibrated if _stem(c) in raw), None)
