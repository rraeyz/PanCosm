"""The Project page."""

from astropy.table import Table
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .kit.table import TableView


class ProjectPage(QWidget):
    """Files in the project and the record of every step run (for reproducibility)."""

    run_selected = Signal(int)  # run id
    rerun_requested = Signal(int)  # run id
    reproduce_requested = Signal(int)  # run id

    def __init__(self, parent=None):
        super().__init__(parent)
        top = QVBoxLayout(self)
        self.name_label = QLabel(self)
        top.addWidget(self.name_label)
        self.methods_open = QPushButton(self.tr("Methods text…"), self)  # the window connects it (File → Methods text…)
        self.methods_open.setEnabled(False)
        top.addWidget(self.methods_open, 0, Qt.AlignLeft)
        self.tabs = QTabWidget(self)  # UI-16.14: Files, History, Methods text, Tasks (Products, Sessions: not yet)
        top.addWidget(self.tabs, 1)
        self.files_list = QListWidget(self)
        self.tabs.addTab(self.files_list, self.tr("Files"))
        history = QWidget(self)
        lay = QVBoxLayout(history)
        self.tabs.addTab(history, self.tr("History"))
        self._methods_tab()
        from .project_tasks import TasksTab

        self.tasks_tab = TasksTab(self)
        self.tabs.addTab(self.tasks_tab, self.tr("Tasks"))
        self.run_ids = []  # the run id of each table row, same order
        self._run_id = None
        self.run_names = (self.tr("Step"), self.tr("Status"), self.tr("Started"), self.tr("Settings"))
        self.runs_table = TableView(self)
        self.runs_table.set_table(Table(names=self.run_names, dtype=(str,) * 4))
        self.runs_table.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.runs_table.view.horizontalHeader().setStretchLastSection(True)
        self.runs_table.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.runs_table.row_chosen.connect(self._selected)
        lay.addWidget(self.runs_table, 1)
        row = QHBoxLayout()
        self.rerun_button = QPushButton(self.tr("Run again with the same inputs and settings"), self)
        self.rerun_button.setEnabled(False)
        self.rerun_button.setToolTip(
            self.tr("Runs the selected step again exactly as before, e.g. after the input files changed")
        )
        self.rerun_button.clicked.connect(lambda: self.rerun_requested.emit(self.selected_run()))
        row.addWidget(self.rerun_button)
        self.reproduce_button = QPushButton(self.tr("Reproduce…"), self)
        self.reproduce_button.setEnabled(False)
        self.reproduce_button.setToolTip(
            self.tr(
                "Runs the step again with the same inputs and settings, keeps a copy of the old products "
                "and compares them"
            )
        )
        self.reproduce_button.clicked.connect(lambda: self.reproduce_requested.emit(self.selected_run()))
        row.addWidget(self.reproduce_button)
        self.python_button = QPushButton(self.tr("Copy as Python"), self)
        self.python_button.setEnabled(False)
        self.python_button.setToolTip(self.tr("The selected step as a line of a Python script (astrowb.api), to copy"))
        self.python_button.clicked.connect(self.copy_python)
        row.addWidget(self.python_button)
        self.recipe_button = QPushButton(self.tr("Save as recipe…"), self)
        self.recipe_button.setEnabled(False)
        self.recipe_button.setToolTip(
            self.tr("The selected step with its settings as an automation: Automation runs it on other files")
        )
        self.recipe_button.clicked.connect(lambda: self.save_recipe())
        row.addWidget(self.recipe_button)
        row.addStretch(1)
        lay.addLayout(row)
        self.details = QPlainTextEdit(self)
        self.details.setReadOnly(True)
        self.details.setPlaceholderText(self.tr("Select a run to see its inputs, settings, results and versions."))
        lay.addWidget(self.details, 1)

    def _methods_tab(self):
        """The methods paragraph of the successful runs, as text to copy into a paper; made when the tab is shown."""
        tab = QWidget(self)
        lay = QVBoxLayout(tab)
        self.methods_text = QPlainTextEdit(self)
        self.methods_text.setReadOnly(True)
        self.methods_text.setPlaceholderText(self.tr("Run steps and the methods paragraph appears here."))
        lay.addWidget(self.methods_text, 1)
        self.methods_button = QPushButton(self.tr("Copy"), self)
        self.methods_button.setToolTip(self.tr("Copies the methods text to the clipboard"))
        self.methods_button.clicked.connect(self.copy_methods)
        lay.addWidget(self.methods_button)
        self.methods_provider = lambda: ""  # the window sets it: the text from the project's full runs
        self.tabs.addTab(tab, self.tr("Methods text"))
        self.tabs.currentChanged.connect(lambda i: i == self.tabs.indexOf(tab) and self.refresh_methods())

    def refresh_methods(self):
        self.methods_text.setPlainText(self.methods_provider())

    def copy_methods(self):
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.methods_text.toPlainText())

    def selected_run(self):
        return self._run_id

    def set_runs(self, runs):
        """Show the project's runs (dicts with id, step, status, started, params); nothing is selected after."""
        import json

        self.run_ids, self._run_id = [r["id"] for r in runs], None
        self.reproduce_button.setEnabled(False)
        self.rerun_button.setEnabled(False)  # the selection is gone with the old rows
        rows = [(r["step"], r["status"], r["started"], json.dumps(r["params"])) for r in runs]
        self.runs_table.set_table(Table(rows=rows, names=self.run_names, dtype=(str,) * 4))

    def _selected(self, row):
        self._run_id = run_id = self.run_ids[row]
        self.rerun_button.setEnabled(True)
        self.reproduce_button.setEnabled(True)
        self.run_selected.emit(run_id)

    def show_run(self, run):
        """Everything recorded about a run, as text (long results are cut)."""
        import json

        self.shown_run = run
        self.python_button.setEnabled(True)
        self.recipe_button.setEnabled(True)
        parts = [f"{run['step']} — {run['status']} — {run['started']}"]
        for key, title in (
            ("inputs", self.tr("Inputs")),
            ("params", self.tr("Settings")),
            ("outputs", self.tr("Results")),
            ("error", self.tr("Error")),
            ("environment", self.tr("Versions")),
        ):
            if run.get(key):
                text = run[key] if isinstance(run[key], str) else json.dumps(run[key], indent=1, default=str)
                parts.append(f"{title}:\n{text[:20000]}")
        self.details.setPlainText("\n\n".join(parts))

    def save_recipe(self, path=None):
        """Into the user's automations (the Automation window lists them) unless another place is chosen."""
        from ..engine import automation

        recipe = recipe_for(self.shown_run)
        if path is None:
            from PySide6.QtWidgets import QFileDialog

            folder = automation.user_dir()
            folder.mkdir(parents=True, exist_ok=True)
            suggestion = str(folder / f"{self.shown_run['step']}.json")
            path, _ = QFileDialog.getSaveFileName(self, self.tr("Save as recipe"), suggestion, "JSON (*.json)")
            if not path:
                return None
        from .messages import guarded

        return guarded(self, automation.save, recipe, path)

    def copy_python(self):
        from PySide6.QtWidgets import QApplication

        text = python_for(self.shown_run)
        QApplication.clipboard().setText(text)
        return text


def recipe_for(run):
    """A recorded run as an automation (a recipe, ARC-12 item 3): the step with its settings; its input files are
    asked for when the recipe runs, so it works on other nights."""
    return {
        "name": f"{run['step']} ({str(run.get('started', ''))[:10]})",
        "description": f"Saved from the project history: {run['step']} as run on {run.get('started', '')}",
        "steps": [{"step": run["step"], "params": dict(run.get("params") or {})}],
    }


def python_for(run):
    """A recorded run as a call of astrowb.api (plans/architecture.md ARC-12 item 3: Copy as Python)."""
    values = {**(run.get("inputs") or {}), **(run.get("params") or {})}
    lines = ["from astrowb import api", "", f"out = api.run({run['step']!r},"]
    lines += [f"    {key}={value!r}," for key, value in values.items()]
    return "\n".join(lines) + "\n)\n"
