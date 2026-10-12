"""Push buttons of the component kit (plans/interface.md "The component kit", UI-3): one `primary` per stage; while
its task runs a button is busy: disabled, its text led by a turning mark.

    run = Button(self.tr("Measure"), "primary", icon="measure")
    run.set_busy(True) ... run.set_busy(False)
"""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QPushButton

KINDS = ("primary", "normal", "quiet", "danger")
SPINNER = "◐◓◑◒"


class Button(QPushButton):
    def __init__(self, text, kind="normal", icon=None, parent=None):
        super().__init__(text, parent)
        if kind not in KINDS:
            raise ValueError(f"unknown button kind {kind}")
        self.kind = kind
        self.setProperty("kind", kind)
        self.setProperty("primary", kind == "primary")  # the theme's primary style
        if icon is not None:
            from .icons import icon as kit_icon

            self.setIcon(kit_icon(icon, self, 16))
        self._text, self._turn = text, 0
        self._timer = QTimer(self, interval=150, timeout=self._spin)

    def set_busy(self, busy):
        if busy and not self._timer.isActive():
            self._text = self.text()
            self._timer.start()
            self._spin()
        elif not busy and self._timer.isActive():
            self._timer.stop()
            self.setText(self._text)
        self.setEnabled(not busy)

    def is_busy(self):
        return self._timer.isActive()

    def _spin(self):
        self._turn = (self._turn + 1) % len(SPINNER)
        self.setText(f"{SPINNER[self._turn]}  {self._text}")
