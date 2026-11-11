"""One labelled row of a form in the component kit (plans/interface.md "The component kit", UI-3): the label in a
fixed column, the control, the unit; a dot appears while the value differs from the default, and a click on the dot
puts the default back.

    row = FormRow(self.tr("Aperture radius"), NumberField(5, 1, 50), unit="px", help=self.tr("Radius of ..."))
    layout.addWidget(row)
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QWidget

from .binding import _parts

LABEL_WIDTH = 132
DOT = "●"


class FormRow(QWidget):
    def __init__(self, label, control, unit=None, help=None, reset=True, parent=None):  # noqa: A002 (the plan's name)
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(label, self)
        self.label.setFixedWidth(LABEL_WIDTH)
        self.label.setWordWrap(True)
        self.label.setBuddy(control)
        self.control = control
        if help:
            self.label.setToolTip(help)
            control.setToolTip(control.toolTip() or help)
        lay.addWidget(self.label)
        lay.addWidget(control, 1)
        self.unit = None
        if unit:
            self.unit = QLabel(unit, self)
            self.unit.setProperty("muted", True)
            lay.addWidget(self.unit)
        self.dot = None
        if reset:
            signal, self._read, self._write = _parts(control)
            self.default = self._read()
            self.dot = QToolButton(self)
            self.dot.setText(DOT)  # a state mark, not an action icon
            self.dot.setAutoRaise(True)
            self.dot.setToolTip(self.tr("Changed from the default; click to put the default back"))
            self.dot.setAccessibleName(self.tr("Reset to the default"))
            self.dot.setFocusPolicy(Qt.TabFocus)
            self.dot.clicked.connect(self.reset)
            lay.addWidget(self.dot)
            signal.connect(lambda *_: self._show_dot())
            self._show_dot()

    def is_changed(self):
        return self.dot is not None and self._read() != self.default

    def reset(self):
        self._write(self.default)
        self._show_dot()

    def _show_dot(self):
        changed = self.is_changed()
        self.dot.setEnabled(changed)
        self.dot.setText(DOT if changed else "")
