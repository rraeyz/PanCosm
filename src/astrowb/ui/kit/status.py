"""The status bar of an area window (plans/interface.md "The component kit", UI-3): read-out at the left in the
monospace font, the message in the middle, progress and Cancel at the right.

    bar = StatusSegments(); window.setStatusBar(bar)
    bar.set_readout("x 1024.3  y 512.7  value 1834.2"); bar.message(self.tr("Saved"), 5000)
    bar.set_progress(62, cancel=task.cancel); bar.set_progress(None)      # None hides it
"""

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QProgressBar, QStatusBar, QToolButton


class StatusSegments(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        from ..theme import MONO
        from .icons import icon

        self.readout = QLabel(self)
        self.readout.setFont(QFont(MONO, self.font().pointSize()))
        self.addWidget(self.readout)  # left; showMessage writes over the middle
        self.progress = QProgressBar(self)
        self.progress.setMaximumWidth(140)
        self.progress.setRange(0, 100)
        self.cancel = QToolButton(self)
        self.cancel.setIcon(icon("close", self, 14))
        self.cancel.setAutoRaise(True)
        self.cancel.setToolTip(self.tr("Cancel"))
        self.addPermanentWidget(self.progress)
        self.addPermanentWidget(self.cancel)
        self._cancel_slot = None
        self.cancel.clicked.connect(lambda: self._cancel_slot and self._cancel_slot())
        self.set_progress(None)

    def set_readout(self, text):
        self.readout.setText(text)

    def message(self, text, ms=0):
        self.showMessage(text, ms)

    def set_progress(self, percent, cancel=None):
        """percent 0–100, -1 for busy without a known end, None to hide; cancel: what the × calls."""
        shown = percent is not None
        self.progress.setVisible(shown)
        self.cancel.setVisible(shown and cancel is not None)
        self._cancel_slot = cancel
        if shown:
            self.progress.setRange(0, 0 if percent < 0 else 100)
            if percent >= 0:
                self.progress.setValue(int(percent))
