"""Input fields of the component kit (plans/interface.md "The component kit", UI-3).

    radius = NumberField(5.0, 1, 50, step=0.5, decimals=1, unit="px", allow_auto=True)
    radius.set_auto(True, shown=4.2)      # "auto" on: the automatic value is shown faint
    radius.valueChanged / radius.auto_changed

A NumberField is a QDoubleSpinBox, so kit/binding.bind works on it unchanged. Typing is checked on every keystroke
(a red border and the reason in the tooltip while the text is not a number in range); Enter commits, Esc puts the
last committed value back; the wheel changes the value only while the field has the focus; Shift steps ×10 and
Ctrl ×0.1.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QPalette, QValidator
from PySide6.QtWidgets import QButtonGroup, QDoubleSpinBox, QHBoxLayout, QLineEdit, QMenu, QToolButton, QWidget

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


class Segmented(QWidget):
    """2–4 exclusive options as joined buttons, instead of radio buttons.

    view = Segmented([("bjd", self.tr("BJD")), ("phase", self.tr("Phase"))], "bjd"); view.changed.connect(...)
    """

    changed = Signal(str)

    def __init__(self, options, value=None, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.group = QButtonGroup(self)
        self.buttons = {}
        for key, text in options:
            b = QToolButton(self)
            b.setText(text)
            b.setCheckable(True)
            b.setAutoRaise(False)
            b.toggled.connect(lambda on, k=key: on and self.changed.emit(k))
            self.group.addButton(b)
            lay.addWidget(b)
            self.buttons[key] = b
        lay.addStretch(1)  # the options stay together at the left of a wide row
        self.setValue(value if value is not None else options[0][0])

    def value(self):
        return next(k for k, b in self.buttons.items() if b.isChecked())

    def setValue(self, key):
        self.buttons[key].setChecked(True)

    def kit_binding(self):
        """(signal, read, write) for kit/binding.bind."""
        return self.changed, self.value, self.setValue


class PathField(QWidget):
    """Choosing files or a folder: typed, dropped (from the file manager or our own windows) or picked with "…";
    the button's arrow lists recent choices. Many files show "48 files — first: light_V_000.fits" with all names in
    the tooltip; a missing file turns the field amber with the reason.

    frames = PathField("files", self.tr("FITS images (*.fits *.fit *.fts)"), "photometry.frames", settings)
    frames.changed.connect(lambda paths: ...)
    """

    changed = Signal(list)
    RECENT = 8

    def __init__(self, kind="file", filters="", recent_key=None, settings=None, parent=None):
        super().__init__(parent)
        if kind not in ("file", "files", "folder"):
            raise ValueError(f"unknown path kind {kind}")
        self.kind, self.filters, self.recent_key, self.settings = kind, filters, recent_key, settings
        self._paths = []
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit(self)
        self.edit.setPlaceholderText(self.tr("Drop files here or choose with …") if kind == "files" else "")
        self.edit.textEdited.connect(lambda text: self.set_paths([text] if text.strip() else [], user=True))
        self.button = QToolButton(self)
        self.button.setText("…")
        self.button.setToolTip(self.tr("Choose…"))
        self.button.clicked.connect(self.choose)
        if recent_key and settings is not None:
            self.button.setPopupMode(QToolButton.MenuButtonPopup)
            self.button.setMenu(QMenu(self.button))
            self.button.menu().aboutToShow.connect(self._recent_menu)
        lay.addWidget(self.edit, 1)
        lay.addWidget(self.button)
        self.setAcceptDrops(True)

    def paths(self):
        return list(self._paths)

    def set_paths(self, paths, user=False):
        self._paths = [str(p) for p in paths]
        n = len(self._paths)
        if n > 1:
            first = Path(self._paths[0]).name
            self.edit.setText(self.tr("{n} files — first: {name}").format(n=n, name=first))
        elif not user:
            self.edit.setText(self._paths[0] if n else "")
        missing = [p for p in self._paths if p and not Path(p).exists()]
        names = "\n".join(self._paths[:40]) + (f"\n… (+{n - 40})" if n > 40 else "")
        if missing:
            reason = self.tr("Not found: {path}").format(path=missing[0])
            self.edit.setStyleSheet(f"QLineEdit {{ border: 1px solid {tokens.DARK['attention']}; }}")
            self.edit.setToolTip(f"{reason}\n\n{names}" if n > 1 else reason)
        else:
            self.edit.setStyleSheet("")
            self.edit.setToolTip(names if n > 1 else "")
        self.changed.emit(self.paths())
        if not missing and self._paths and not user:
            self._remember()

    def choose(self):
        from PySide6.QtWidgets import QFileDialog

        start = self._paths[0] if self._paths else ""
        if self.kind == "folder":
            got = QFileDialog.getExistingDirectory(self, self.tr("Choose a folder"), start)
            got = [got] if got else []
        elif self.kind == "files":
            got = QFileDialog.getOpenFileNames(self, self.tr("Choose files"), start, self.filters)[0]
        else:
            got = QFileDialog.getOpenFileName(self, self.tr("Choose a file"), start, self.filters)[0]
            got = [got] if got else []
        if got:
            self.set_paths(got)

    # dropping
    def dragEnterEvent(self, event):
        if any(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.set_paths(paths if self.kind == "files" else paths[:1])
            event.acceptProposedAction()

    # recent choices
    def _recent(self):
        stored = self.settings.get(f"recent.{self.recent_key}") if self.recent_key and self.settings else None
        return stored if isinstance(stored, list) else []

    def _remember(self):
        if not (self.recent_key and self.settings is not None):
            return
        entry = self.paths()
        recent = [entry] + [r for r in self._recent() if r != entry]
        self.settings.set(f"recent.{self.recent_key}", recent[: self.RECENT])

    def _recent_menu(self):
        menu = self.button.menu()
        menu.clear()
        for entry in self._recent():
            name = entry[0] if len(entry) == 1 else self.tr("{n} files — first: {name}").format(
                n=len(entry), name=Path(entry[0]).name)  # fmt: skip
            menu.addAction(name, lambda e=entry: self.set_paths(e))
        if menu.isEmpty():
            menu.addAction(self.tr("No recent choices")).setEnabled(False)

    def kit_binding(self):
        """(signal, read, write) for kit/binding.bind: one path as a string, several as a list."""
        one = self.kind != "files"
        return (
            self.changed,
            lambda: (self._paths[0] if self._paths else "") if one else self.paths(),
            lambda v: self.set_paths([v] if isinstance(v, str) and v else list(v or [])),
        )
