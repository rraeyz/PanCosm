"""ObjectField: an object name that is resolved on request (planning.resolve: SIMBAD with a local cache, so a name seen
before works offline) and shows what was found. Every failure is said in the answer line, none raises."""

from PySide6.QtCore import QCoreApplication, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from .buttons import Button

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ObjectField", "…") calls


class ObjectField(QWidget):
    resolved = Signal(str, dict)  # the name as typed, the target {name, ra, dec, vmag, source}

    def __init__(self, run_step, cache_file, placeholder="", button="Find", parent=None):
        """run_step(step, params, on_done=, on_fail=) is the window's engine call; cache_file() the cache's path."""
        super().__init__(parent)
        self._run_step, self._cache_file = run_step, cache_file
        self.precheck = None  # optional: returns a sentence that stops the lookup, or None
        self.edit = QLineEdit(self)
        self.edit.setPlaceholderText(placeholder)
        self.button = Button(button, "normal", parent=self)
        self.answer = QLabel(self)
        self.answer.setWordWrap(True)
        self.answer.setProperty("muted", True)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.edit, 1)
        row.addWidget(self.button)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(row)
        lay.addWidget(self.answer)
        self.button.clicked.connect(self.start)
        self.edit.returnPressed.connect(self.button.click)

    def start(self):
        name = self.edit.text().strip()
        if not name:
            return
        if self.precheck and (stop := self.precheck()):
            self.answer.setText(stop)
            return
        self.answer.setText(translate("ObjectField", "Looking up {name}…").format(name=name))
        self._run_step(
            "planning.resolve",
            {"name": name, "cache_file": str(self._cache_file())},
            on_done=lambda out: self._found(name, out["target"]),
            on_fail=self._failed,
        )

    def _found(self, name, target):
        self.answer.setText(
            translate("ObjectField", "{name}: RA {ra:.4f}°, Dec {dec:+.4f}° ({source})").format(
                name=target.get("name") or name, ra=target["ra"], dec=target["dec"], source=target.get("source", "")
            )
        )
        self.resolved.emit(name, target)

    def _failed(self, message):
        from ..messages import translate as message_text

        self.answer.setText(message_text(message))
