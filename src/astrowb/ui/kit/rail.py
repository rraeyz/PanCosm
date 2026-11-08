"""The stages of an area window (plans/interface.md "Anatomy of an area window", UI-3; the frame is UI-4).

    rail = StageRail([("images", self.tr("Images")), ("stars", self.tr("Stars")), ("measure", self.tr("Measure"))])
    rail.stage_chosen.connect(show_stage); rail.set_state("images", "done"); rail.set_current("stars")
    panel = StagePanel(self.tr("Stars"), help="photometry-choosing-images-stars")
    panel.add(...); panel.set_primary(Button(self.tr("Measure"), "primary")); panel.set_status("…")

The rail shows the stages' names (no numbers: "1 ✓ 2 ○" read as a child's guide, user-feedback UF-19), a done
stage with a quiet ✓ and one needing attention with "!" after its name, the current one highlighted. Unpinned, it is
48 px wide with only those marks and the names in the tooltips (widening on hover squeezed the stage's controls).
The panel's content scrolls; its status line and primary action stay in sight at the bottom.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .icons import icon

NARROW, WIDE = 48, 150
MARKS = {"empty": "", "current": "", "done": "✓", "attention": "!"}
NARROW_MARKS = {"empty": "○", "current": "●", "done": "✓", "attention": "!"}


class StageRail(QWidget):
    stage_chosen = Signal(str)
    pinned_changed = Signal(bool)  # the window widens its stage panel by the names' room

    def __init__(self, stages, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)
        self.buttons, self.names, self.states, self.current = {}, {}, {}, None
        self.pinned = True  # the names shown from the start
        for i, (key, name) in enumerate(stages, 1):
            b = QToolButton(self)
            b.setCheckable(True)
            b.setAutoRaise(True)
            b.setToolButtonStyle(Qt.ToolButtonTextOnly)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setToolTip(name)
            b.setAccessibleName(name)
            b.clicked.connect(lambda _on, k=key: self.choose(k))
            lay.addWidget(b)
            self.buttons[key], self.names[key], self.states[key] = b, (i, name), "empty"
        lay.addStretch(1)
        self.pin = QToolButton(self)
        self.pin.setCheckable(True)
        self.pin.setAutoRaise(True)
        self.pin.setIcon(icon("next", self, 16))
        self.pin.setToolTip(self.tr("Keep the names shown"))
        self.pin.toggled.connect(self.set_pinned)
        lay.addWidget(self.pin)
        self.pin.setChecked(True)
        self._expanded = True
        self._show()

    def choose(self, key):
        self.set_current(key)
        self.stage_chosen.emit(key)

    def set_current(self, key):
        self.current = key
        self._show()

    def set_state(self, key, state):
        if state not in MARKS:
            raise ValueError(f"unknown stage state {state}")
        self.states[key] = state
        self._show()

    def set_pinned(self, on):
        self.pinned = bool(on)
        self._expanded = self.pinned
        self._show()
        self.pinned_changed.emit(self.pinned)

    def _show(self):
        self.setFixedWidth(WIDE if self._expanded else NARROW)
        for key, b in self.buttons.items():
            _number, name = self.names[key]
            state = "current" if key == self.current and self.states[key] == "empty" else self.states[key]
            b.setText(f"{name}  {MARKS[state]}".rstrip() if self._expanded else NARROW_MARKS[state])
            b.setChecked(key == self.current)


class StagePanel(QWidget):
    help_requested = Signal(str)

    def __init__(self, title, help=None, parent=None):  # noqa: A002 (the plan's name)
        super().__init__(parent)
        self.help = help
        self.setProperty("help_anchor", help)
        lay = QVBoxLayout(self)
        head = QHBoxLayout()
        self.title = QLabel(f"<b>{title}</b>", self)
        head.addWidget(self.title, 1)
        if help:
            ask = QToolButton(self)
            ask.setIcon(icon("help", self, 16))
            ask.setAutoRaise(True)
            ask.setToolTip(self.tr("Help on this stage"))
            ask.clicked.connect(lambda: self.help_requested.emit(self.help))
            head.addWidget(ask)
        lay.addLayout(head)
        scroll = QScrollArea(self)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget(scroll)
        self.body = QVBoxLayout(inner)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.addStretch(1)
        scroll.setWidget(inner)
        lay.addWidget(scroll, 1)
        self.status = QLabel(self)
        self.status.setProperty("muted", True)
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.bottom = QVBoxLayout()
        lay.addLayout(self.bottom)
        self.primary = None

    def add(self, widget):
        """Add a widget to the scrolling content (above the stretch). A page that scrolls itself takes the whole
        height: above the stretch it kept its hint's height and scrolled with free room below (user-feedback UF-11)."""
        grows = isinstance(widget, QScrollArea)
        self.body.insertWidget(self.body.count() - 1, widget, 1 if grows else 0)
        if grows:
            self.body.setStretch(self.body.count() - 1, 0)

    def set_title(self, title):
        self.title.setText(f"<b>{title}</b>")

    def set_status(self, text):
        self.status.setText(text)

    def set_primary(self, button):
        if self.primary is not None:
            self.bottom.removeWidget(self.primary)
            self.primary.deleteLater()
        self.primary = button
        self.bottom.addWidget(button)
