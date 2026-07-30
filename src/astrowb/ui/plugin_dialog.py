"""A form generated from a plugin step: one field per input and parameter, values parsed as JSON
when possible (numbers, lists, true/false), otherwise kept as text (file paths)."""

import json

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout


def parse(text):
    text = text.strip()
    if text == "":
        return None
    try:
        return json.loads(text)
    except ValueError:
        return text


class PluginDialog(QDialog):
    def __init__(self, step, parent=None):
        super().__init__(parent)
        self.step = step
        self.setWindowTitle(step.id)
        lay = QVBoxLayout(self)
        doc = (step.func.__doc__ or "").strip()
        if doc:
            lay.addWidget(QLabel(doc, self, wordWrap=True))
        form = QFormLayout()
        self.fields = {}
        for name in step.inputs + step.optional:
            edit = QLineEdit(self)
            edit.setPlaceholderText(self.tr("required") if name in step.inputs else self.tr("optional"))
            form.addRow(name, edit)
            self.fields[("in", name)] = edit
        for name, default in step.defaults.items():
            edit = QLineEdit(json.dumps(default) if not isinstance(default, str) else default, self)
            form.addRow(name, edit)
            self.fields[("param", name)] = edit
        lay.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def values(self):
        inputs, params = {}, {}
        for (kind, name), edit in self.fields.items():
            v = parse(edit.text())
            if v is None:
                continue
            (inputs if kind == "in" else params)[name] = v
        return inputs, params
