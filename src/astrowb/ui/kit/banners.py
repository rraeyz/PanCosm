"""In-window messages of the component kit (plans/interface.md "The component kit", UI-3): never a modal dialog
for information.

    banner = InfoBanner("attention", self.tr("3 frames have no time stamp"), [(self.tr("Show them"), show)])
    layout.insertWidget(0, banner)           # dismissible: the × hides it and emits dismissed
    Badge(self.tr("calibrated"), "ok")       # a small state label
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QToolButton, QWidget

from . import tokens

KINDS = {"info": ("accent", "info"), "ok": ("ok", "info"), "attention": ("attention", "warning"),
         "error": ("error", "error")}  # fmt: skip


def _colours(widget, kind):
    """(edge colour, text colour) of a kind in the theme the widget shows (dark or light by its window colour)."""
    dark = widget.palette().window().color().lightness() < 128
    table = tokens.DARK if dark else tokens.LIGHT
    return table[KINDS[kind][0]], table["text"]


class InfoBanner(QWidget):
    dismissed = Signal()

    def __init__(self, kind, text, actions=(), parent=None):
        super().__init__(parent)
        if kind not in KINDS:
            raise ValueError(f"unknown banner kind {kind}")
        self.kind = kind
        self.setObjectName("InfoBanner")
        self.setAttribute(Qt.WA_StyledBackground, True)
        edge, ink = _colours(self, kind)
        self.setStyleSheet(
            f"#InfoBanner {{ border: 1px solid {edge}; border-left: 4px solid {edge}; border-radius: 6px; }}"
            f"#InfoBanner QLabel {{ color: {ink}; }}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 6, 6)
        from .icons import icon

        mark = QLabel(self)
        mark.setPixmap(icon(KINDS[kind][1], self, 18).pixmap(18, 18))
        lay.addWidget(mark)
        self.label = QLabel(text, self)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.label, 1)
        self.buttons = []
        for name, slot in actions:
            b = QPushButton(name, self)
            b.clicked.connect(slot)
            lay.addWidget(b)
            self.buttons.append(b)
        self.close_button = QToolButton(self)
        self.close_button.setIcon(icon("close", self, 16))
        self.close_button.setAutoRaise(True)
        self.close_button.setToolTip(self.tr("Dismiss"))
        self.close_button.setAccessibleName(self.tr("Dismiss"))
        self.close_button.clicked.connect(self.dismiss)
        lay.addWidget(self.close_button)

    def text(self):
        return self.label.text()

    def dismiss(self):
        self.hide()
        self.dismissed.emit()


class Badge(QLabel):
    """A small rounded state label: "calibrated", "from cache", "simulated"."""

    def __init__(self, text, kind="info", parent=None):
        super().__init__(text, parent)
        if kind not in KINDS:
            raise ValueError(f"unknown badge kind {kind}")
        edge, _ink = _colours(self, kind)
        self.setStyleSheet(f"QLabel {{ color: {edge}; border: 1px solid {edge}; border-radius: 8px; padding: 0 6px; }}")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
