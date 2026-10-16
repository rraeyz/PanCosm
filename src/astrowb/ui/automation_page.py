"""Automation: pick a ready template or build a chain of steps, fill in its inputs and run it.

Each step runs as a normal task (Tasks panel, recorded in the project). An automation may also carry an
observing sequence, which is sent to the Observing window.
"""

import copy
import json
import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..engine import automation, steps
from .kit.widgets import _title
from .messages import translate
from .setting_names import setting_name


def _json_or_text(text):
    try:
        return json.loads(text)
    except ValueError:
        return text


class AutomationPage(QWidget):
    run_requested = Signal(object, dict)  # automation, inputs
    sequence_requested = Signal(dict)  # observing target spec for the Observe page

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        from .i18n import system_language

        # the interface's language: the one chosen, else the system's (as the interface itself does)
        self.lang = settings.get("ui.language") or system_language()
        self.auto = None
        self.values = {}  # input texts survive editing the steps
        split = QSplitter(Qt.Horizontal, self)

        left = QWidget(self)
        ll = QVBoxLayout(left)
        ll.addWidget(_title(self.tr("Automation"), self))
        self.list = QListWidget(self)
        self.list.setWordWrap(True)  # long template names wrap: they were cut, with a sideways scroll bar
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setResizeMode(QListWidget.Adjust)
        self.list.currentRowChanged.connect(self._select)
        ll.addWidget(self.list, 1)
        row = QHBoxLayout()
        self.new_button = new = QPushButton(self.tr("New"), self)
        new.clicked.connect(self.new)
        new.setToolTip(self.tr("An empty automation to fill with steps"))
        self.save_button = save = QPushButton(self.tr("Save as…"), self)
        save.clicked.connect(self._save_dialog)
        save.setToolTip(self.tr("Saves the automation under a name, to run it again on other data"))
        row.addWidget(new)
        row.addWidget(save)
        ll.addLayout(row)
        split.addWidget(left)

        mid = QWidget(self)
        ml = QVBoxLayout(mid)
        self.description = QLabel(self)
        self.description.setWordWrap(True)
        self.description.setProperty("muted", True)
        ml.addWidget(self.description)
        ml.addWidget(QLabel(self.tr("Steps, in order"), self))
        self.steps = QListWidget(self)
        self.steps.currentRowChanged.connect(self._show_step)
        ml.addWidget(self.steps, 1)
        self.step_choice = QComboBox(self)
        steps.get("fits.save_as")  # loads the built-in steps and plugins
        from .step_names import step_name

        for sid in sorted(steps.REGISTRY, key=step_name):  # the user reads names; the id is kept as the item's data
            self.step_choice.addItem(step_name(sid), sid)
            self.step_choice.setItemData(self.step_choice.count() - 1, sid, Qt.ToolTipRole)
        self.step_choice.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.step_choice.setMinimumContentsLength(14)  # long step ids do not widen the page; the list shows them whole
        self.step_choice.setToolTip(
            self.tr("Every task of the application as a step (calibrate, stack, photometry, period search…)")
        )
        self.add_button = add = QPushButton(self.tr("Add step"), self)
        add.clicked.connect(lambda: self.add_step(self.step_choice.currentData()))
        add.setToolTip(self.tr("Adds the chosen step at the end; its settings appear below"))
        ml.addWidget(self.step_choice)  # one above the other: the page fits narrow windows in every language
        ml.addWidget(add)
        row = QHBoxLayout()
        self.step_buttons = []  # Remove, Up, Down
        for text, slot, tip in (
            (self.tr("Remove"), self._remove, self.tr("Removes the selected step")),
            (self.tr("Up"), lambda: self._move(-1), self.tr("Moves the selected step one place earlier")),
            (self.tr("Down"), lambda: self._move(1), self.tr("Moves the selected step one place later")),
        ):
            b = QPushButton(text, self)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            row.addWidget(b)
            self.step_buttons.append(b)
        ml.addLayout(row)
        hint = QLabel(self.tr("Settings of the selected step (input ← data name, or a value)"), self)
        hint.setWordWrap(True)
        ml.addWidget(hint)
        self.settings_table = QTableWidget(0, 2, self)
        self.settings_table.setHorizontalHeaderLabels([self.tr("Setting"), self.tr("Value")])
        self.settings_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.settings_table.verticalHeader().hide()
        self.settings_table.itemChanged.connect(self._setting_changed)
        ml.addWidget(self.settings_table, 1)
        split.addWidget(mid)

        right = QWidget(self)
        rl = QVBoxLayout(right)
        rl.addWidget(QLabel(self.tr("Inputs"), self))
        self.form = QFormLayout()
        self.form.setRowWrapPolicy(QFormLayout.WrapAllRows)  # long labels above their fields
        rl.addLayout(self.form)
        self.run_button = QPushButton(self.tr("Run"), self)
        self.run_button.setProperty("primary", True)
        self.run_button.clicked.connect(self._run)
        self.run_button.setToolTip(
            self.tr("Runs the steps one after the other with these inputs; each step's result is kept in the project")
        )
        self.sequence_button = QPushButton(self.tr("To the Observing window"), self)
        self.sequence_button.setToolTip(self.tr("Send sequence to the Observing window"))
        self.sequence_button.clicked.connect(self._send_sequence)
        rl.addWidget(self.run_button)  # one per line: the page fits narrow windows in every language
        rl.addWidget(self.sequence_button)
        self.after_night = QCheckBox(self.tr("Process after the sequence"), self)
        self.after_night.setToolTip(
            self.tr("Run the processing when this sequence has finished.")
            + " "
            + self.tr("Frames of a remote observatory are copied to this computer first.")
        )
        rl.addWidget(self.after_night)
        self.status = QLabel(self)
        self.status.setWordWrap(True)
        rl.addWidget(self.status)
        self.result = QPlainTextEdit(self)
        self.result.setReadOnly(True)
        rl.addWidget(self.result, 1)
        split.addWidget(right)
        split.setSizes([330, 420, 520])
        QVBoxLayout(self).addWidget(split)
        self.refresh()

    # --- list -----------------------------------------------------------------
    def refresh(self, select_path=None):
        self.found = automation.available()
        self.list.blockSignals(True)
        self.list.clear()
        for a in self.found:
            name = automation.text(a["name"], self.lang)
            self.list.addItem(self.tr("{name} (template)").format(name=name) if a["template"] else name)
        self.list.blockSignals(False)
        paths = [a["path"] for a in self.found]
        self.list.setCurrentRow(paths.index(select_path) if select_path in paths else 0)

    def _select(self, row):
        if 0 <= row < len(self.found):
            self.set_automation(copy.deepcopy(self.found[row]))

    def new(self):
        self.list.clearSelection()
        self.set_automation({"name": self.tr("New automation"), "steps": []})

    def set_automation(self, auto):
        self.auto = auto
        self.description.setText(automation.text(auto.get("description"), self.lang))
        self.sequence_button.setVisible("sequence" in auto)
        self.after_night.setVisible("sequence" in auto)
        self._fill_steps()

    def _send_sequence(self):
        self.armed = self.auto if self.after_night.isChecked() else None
        self.sequence_requested.emit(self.auto["sequence"])

    def night_finished(self, folder):
        """The sequence sent from here has ended: process its folder (when asked to)."""
        auto, self.armed = getattr(self, "armed", None), None
        if auto is None:
            return
        self.set_automation(auto)
        if "folder" in self.edits:
            self.edits["folder"].setText(folder)
        self._run()

    def _save_dialog(self):
        name, ok = QInputDialog.getText(
            self, self.tr("Save automation"), self.tr("Name:"), text=automation.text(self.auto["name"], self.lang)
        )
        if ok and name.strip():
            self.save_as(name.strip())

    def save_as(self, name):
        self.auto["name"] = name
        file = re.sub(r"[^\w-]+", "_", name).strip("_") or "automation"
        path = automation.save(self.auto, automation.user_dir() / f"{file}.json")
        self.refresh(str(path))
        return path

    # --- steps ----------------------------------------------------------------
    def _fill_steps(self, row=0):
        from .step_names import step_name

        self.steps.blockSignals(True)
        self.steps.clear()
        for i, entry in enumerate(self.auto["steps"]):
            each = self.tr(" — for each {name}").format(name=entry["each"]) if entry.get("each") else ""
            self.steps.addItem(f"{i + 1}. {step_name(entry['step'])}{each}")
            self.steps.item(i).setToolTip(entry["step"])
        self.steps.blockSignals(False)
        self.steps.setCurrentRow(min(row, self.steps.count() - 1))
        self._show_step(self.steps.currentRow())
        self._fill_inputs()

    def add_step(self, step_id):
        self.auto["steps"].append({"step": step_id})
        self._fill_steps(len(self.auto["steps"]) - 1)

    def _remove(self):
        r = self.steps.currentRow()
        if r >= 0:
            del self.auto["steps"][r]
            self._fill_steps(max(r - 1, 0))

    def _move(self, d):
        r, s = self.steps.currentRow(), self.auto["steps"]
        if 0 <= r and 0 <= r + d < len(s):
            s[r], s[r + d] = s[r + d], s[r]
            self._fill_steps(r + d)

    def _show_step(self, row):
        t = self.settings_table
        t.blockSignals(True)
        t.setRowCount(0)
        if 0 <= row < len(self.auto["steps"]):
            entry = self.auto["steps"][row]
            s = steps.get(entry["step"])
            rows = [("input", n, entry.get("inputs", {}).get(n, n)) for n in s.inputs + s.optional]
            rows += [("param", k, json.dumps(entry.get("params", {}).get(k, v))) for k, v in s.defaults.items()]
            for kind, name, value in rows:
                r = t.rowCount()
                t.insertRow(r)
                shown = setting_name(entry["step"], name)  # the key stays in the tooltip and in the saved file
                label = QTableWidgetItem(f"← {shown}" if kind == "input" else shown)
                label.setToolTip(name)
                label.setFlags(Qt.ItemIsEnabled)
                label.setData(Qt.UserRole, (kind, name))
                t.setItem(r, 0, label)
                t.setItem(r, 1, QTableWidgetItem(value))
        t.blockSignals(False)

    def _setting_changed(self, item):
        entry = self.auto["steps"][self.steps.currentRow()]
        kind, name = self.settings_table.item(item.row(), 0).data(Qt.UserRole)
        text = item.text().strip()
        if kind == "input":
            links = entry.setdefault("inputs", {})
            links.pop(name, None) if text in ("", name) else links.__setitem__(name, text)
        else:
            entry.setdefault("params", {})[name] = _json_or_text(text)
        self._fill_inputs()

    # --- inputs and running ---------------------------------------------------
    def input_names(self):
        declared = list(self.auto.get("inputs", {}))
        return declared + [k for k in automation.needed(self.auto) if k not in declared]

    def _fill_inputs(self):
        while self.form.rowCount():
            self.form.removeRow(0)
        self.edits = {}
        specs = self.auto.get("inputs", {})
        for name in self.input_names():
            spec = specs.get(name, {})
            edit = QLineEdit(self.values.get(name, ""), self)
            edit.textChanged.connect(lambda text, n=name: self.values.__setitem__(n, text))
            self.edits[name] = edit
            edit.setToolTip(self.tr("A value, a file or a folder for this input of the automation"))
            row = QHBoxLayout()
            row.addWidget(edit, 1)
            if spec.get("kind") in ("folder", "file", "files"):
                b = QPushButton("…", self)
                b.setToolTip(self.tr("Choose in a dialog"))
                b.clicked.connect(lambda _=False, e=edit, k=spec["kind"]: self._browse(e, k))
                row.addWidget(b)
            self.form.addRow(automation.text(spec.get("label"), self.lang) or name, row)
            self.form.labelForField(row).setWordWrap(True)  # long labels wrap instead of widening the page

    def _browse(self, edit, kind):
        if kind == "folder":
            path = QFileDialog.getExistingDirectory(self, self.tr("Choose a folder"))
        elif kind == "file":
            path = QFileDialog.getOpenFileName(self, self.tr("Choose a file"))[0]
        else:
            path = "; ".join(QFileDialog.getOpenFileNames(self, self.tr("Choose files"))[0])
        if path:
            edit.setText(path)

    def inputs(self):
        specs, out = self.auto.get("inputs", {}), {}
        for name, edit in self.edits.items():
            if edit.text().strip():
                kind = specs.get(name, {}).get("kind")
                out[name] = automation.parse(kind, edit.text()) if kind else _json_or_text(edit.text().strip())
        return out

    def _run(self):
        try:
            inputs = self.inputs()
            automation.check(self.auto, inputs)
        except (ValueError, steps.MissingInput) as e:
            self.status.setText(self.tr("Cannot run: {e}").format(e=translate(e)))
            return
        self.result.clear()
        self.run_requested.emit(self.auto, inputs)

    def step_started(self, n, step_id):
        from .step_names import step_name

        self.status.setText(self.tr("Running step {n}: {step}").format(n=n, step=step_name(step_id)))

    def finished(self, data, last_outputs):
        self.status.setText(self.tr("Finished."))
        self.result.setPlainText(json.dumps(last_outputs, indent=1, default=str)[:20000])

    def failed(self, message):
        self.status.setText(self.tr("Stopped: {e}").format(e=translate(message)))
