"""Input fields of the component kit (plans/interface.md "The component kit", UI-3).

    radius = NumberField(5.0, 1, 50, step=0.5, decimals=1, unit="px", allow_auto=True)
    radius.set_auto(True, shown=4.2)      # "auto" on: the automatic value is shown faint
    radius.valueChanged / radius.auto_changed

A NumberField is a QDoubleSpinBox, so kit/binding.bind works on it unchanged. Typing is checked on every keystroke
(a red border and the reason in the tooltip while the text is not a number in range); Enter commits, Esc puts the
last committed value back; the wheel changes the value only while the field has the focus; Shift steps ×10 and
Ctrl ×0.1.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QPalette, QValidator
from PySide6.QtWidgets import QDoubleSpinBox

from . import tokens


class NumberField(QDoubleSpinBox):
    auto_changed = Signal(bool)

    def __init__(self, value=0.0, minimum=0.0, maximum=1e9, step=1.0, decimals=2, unit="", allow_auto=False,
                 parent=None):  # fmt: skip
        self._auto, self._shown = False, None  # before Qt calls textFromValue
        super().__init__(parent)
        self.setRange(minimum, maximum)
        self.setDecimals(decimals)
        self.setSingleStep(step)
        if unit:
            self.setSuffix(f" {unit}")  # shortcut: unit in the text colour, not faint; paint it in UI-3
        self.setValue(value)
        self.setKeyboardTracking(False)  # valueChanged on Enter or focus out, not on every keystroke
        self.setFocusPolicy(Qt.StrongFocus)  # no focus (and so no change) from the wheel alone
        self.setAccelerated(True)
        self.valueChanged.connect(lambda _v: self._check(self.lineEdit().text()))
        self.lineEdit().textEdited.connect(self._check)
        self.auto_action = None
        if allow_auto:
            self.auto_action = QAction(self.tr("auto"), self)
            self.auto_action.setCheckable(True)
            self.auto_action.setToolTip(self.tr("Let the program choose this value"))
            self.auto_action.toggled.connect(lambda on: self.set_auto(on, self._shown))
            self.lineEdit().addAction(self.auto_action, self.lineEdit().ActionPosition.TrailingPosition)

    # automatic value
    def is_auto(self):
        return self._auto

    def set_auto(self, on, shown=None):
        """Auto on: the field shows the automatic value `shown` (when known) faint; typing a value turns auto off."""
        on = bool(on)
        self._shown = shown
        changed = on != self._auto
        self._auto = on
        if self.auto_action is not None and self.auto_action.isChecked() != on:
            self.auto_action.blockSignals(True)
            self.auto_action.setChecked(on)
            self.auto_action.blockSignals(False)
        self._paint()
        if changed:
            self.auto_changed.emit(on)

    def textFromValue(self, value):
        if self._auto:
            return self.tr("auto") if self._shown is None else super().textFromValue(self._shown)
        return super().textFromValue(value)

    def _paint(self):
        faint = self.palette().color(QPalette.PlaceholderText).name()
        self.lineEdit().setStyleSheet(f"color: {faint};" if self._auto else "")
        self.lineEdit().setText(self.textFromValue(self.value()) + self.suffix())

    # typing
    def validate(self, text, pos):
        if self._auto:
            return QValidator.Acceptable, text, pos
        return super().validate(text, pos)

    def _check(self, text):
        if self._auto:
            self.set_auto(False)
        state = super().validate(text, 0)[0] if not self._auto else QValidator.Acceptable
        bad = state != QValidator.Acceptable
        self.setProperty("invalid", bad)
        low, high = self.textFromValue(self.minimum()), self.textFromValue(self.maximum())
        self.setToolTip(self.tr("A number from {low} to {high}").format(low=low, high=high) if bad else "")
        self.setStyleSheet(f"QDoubleSpinBox {{ border: 1px solid {tokens.DARK['error']}; }}" if bad else "")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:  # the value only changes on Enter, so the shown text goes back to it
            self._paint()
            self._check(self.lineEdit().text())
            return
        if event.key() in (Qt.Key_Up, Qt.Key_Down):  # our own steps: Qt's Ctrl ×10 would undo Ctrl = ×0.1
            self.stepBy(1 if event.key() == Qt.Key_Up else -1, event.modifiers())
            return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()  # the scroll goes to the panel, the value stays
            return
        steps = round(event.angleDelta().y() / 120)  # our own steps: Qt's Ctrl+wheel ×10 would undo Ctrl = ×0.1
        if steps:
            self.stepBy(steps, event.modifiers())
        event.accept()

    def stepBy(self, steps, mods=Qt.NoModifier):
        factor = 10.0 if mods & Qt.ShiftModifier else 0.1 if mods & Qt.ControlModifier else 1.0
        if self._auto:
            self.set_auto(False)
        self.setValue(self.value() + steps * factor * self.singleStep())
