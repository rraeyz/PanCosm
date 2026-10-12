"""A brief confirmation at the bottom right of a window (plans/interface.md "The component kit", UI-3), gone after
5 s; never for errors (those are InfoBanner or the error dialog).

    Toast.show_in(window, self.tr("Saved to {path}").format(path=p), (self.tr("Show in folder"), reveal))
"""

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

SECONDS = 5
MARGIN = 16


class Toast(QFrame):
    def __init__(self, parent, text, action=None):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setFrameShape(QFrame.StyledPanel)
        self.setAutoFillBackground(True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 8, 8)
        self.label = QLabel(text, self)
        lay.addWidget(self.label)
        self.button = None
        if action is not None:
            name, slot = action
            self.button = QPushButton(name, self)
            self.button.clicked.connect(slot)
            self.button.clicked.connect(self.close)
            lay.addWidget(self.button)
        self.timer = QTimer(self, singleShot=True, interval=SECONDS * 1000, timeout=self.close)
        self.setAttribute(Qt.WA_DeleteOnClose)
        parent.installEventFilter(self)  # follow the window's corner when it is resized

    @classmethod
    def show_in(cls, window, text, action=None):
        """Show a toast in the window's bottom right corner; an earlier toast there is replaced."""
        for old in window.findChildren(Toast):
            old.close()
        toast = cls(window, text, action)
        toast.adjustSize()
        toast._place()
        toast.show()
        toast.raise_()
        toast.timer.start()
        return toast

    def _place(self):
        p = self.parentWidget()
        self.move(p.width() - self.width() - MARGIN, p.height() - self.height() - MARGIN)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Resize:
            self._place()
        return False
