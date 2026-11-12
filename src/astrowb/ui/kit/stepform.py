"""A form made from a step's described settings (plans/automation.md AUT-1 item 5): one FormRow per setting with
the control its kind asks for, its label, unit and help translated, a reset dot to the default, the advanced ones
folded. Plugins, automations and recipes get the same form a hand-built panel would show.

    form = StepForm(steps.get("calibration.run")); form.values()   # {"sigma": 3.0, ...}
"""

import json

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from .fields import ChoiceField, NumberField, Toggle
from .forms import FormRow
from .sections import Section


def _tr(text):
    return QCoreApplication.translate("Steps", text) if text else ""


def control_for(p, parent):
    """(widget, read()) for one setting; a value left empty (None) means "the step decides"."""
    if p.kind in ("int", "float") and p.default is not None:
        low = p.min if p.min is not None else -1e12
        high = p.max if p.max is not None else 1e12
        decimals = 0 if p.kind == "int" else 4
        field = NumberField(p.default, low, high, 1.0, decimals, parent=parent)
        return field, (lambda: int(field.value()) if p.kind == "int" else field.value())
    if p.kind == "bool":
        field = Toggle("", bool(p.default), parent)
        return field, field.isChecked
    if p.kind == "choice":
        field = ChoiceField([(c, str(c)) for c in p.choices], p.default, parent)
        return field, field.value
    shown = "" if p.default is None else (p.default if isinstance(p.default, str) else json.dumps(p.default))
    field = QLineEdit(shown, parent)
    if p.default is None:
        field.setPlaceholderText(QCoreApplication.translate("StepForm", "automatic"))

    def read():
        text = field.text().strip()
        if not text:
            return None if p.default is None or p.kind in ("int", "float") else ("" if p.kind == "text" else p.default)
        if p.kind in ("text", "band", "file", "folder", "expression"):
            return text
        try:
            return json.loads(text)
        except ValueError:
            return text

    return field, read


class StepForm(QWidget):
    def __init__(self, step, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.readers, self.rows = {}, {}
        more = None
        for p in step.params:
            control, read = control_for(p, self)
            row = FormRow(_tr(p.label) or p.name, control, unit=p.unit, help=_tr(p.help), reset=False)
            if p.advanced:
                if more is None:
                    more = Section(QCoreApplication.translate("StepForm", "More settings"), folded=True, parent=self)
                more.body.addWidget(row)
            else:
                lay.addWidget(row)
            self.readers[p.name], self.rows[p.name] = read, row
        if more is not None:
            lay.addWidget(more)
        lay.addStretch(1)

    def values(self):
        return {name: read() for name, read in self.readers.items()}
