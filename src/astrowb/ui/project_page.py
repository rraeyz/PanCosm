"""The Project page."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)


class ProjectPage(QWidget):
    """Files in the project and the record of every step run (for reproducibility)."""

    run_selected = Signal(int)  # run id
    rerun_requested = Signal(int)  # run id

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        self.name_label = QLabel(self)
        lay.addWidget(self.name_label)
        lay.addWidget(QLabel(self.tr("Files"), self))
        self.files_list = QListWidget(self)
        lay.addWidget(self.files_list, 1)
        lay.addWidget(QLabel(self.tr("History"), self))
        self.runs_table = QTableWidget(0, 4, self)
        self.runs_table.setHorizontalHeaderLabels(
            [self.tr("Step"), self.tr("Status"), self.tr("Started"), self.tr("Settings")]
        )
        self.runs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.runs_table.horizontalHeader().setStretchLastSection(True)
        self.runs_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.runs_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.runs_table.itemSelectionChanged.connect(self._selected)
        lay.addWidget(self.runs_table, 1)
        row = QHBoxLayout()
        self.rerun_button = QPushButton(self.tr("Run again with the same inputs and settings"), self)
        self.rerun_button.setEnabled(False)
        self.rerun_button.setToolTip(
            self.tr("Runs the selected step again exactly as before, e.g. after the input files changed")
        )
        self.rerun_button.clicked.connect(lambda: self.rerun_requested.emit(self.selected_run()))
        row.addWidget(self.rerun_button)
        row.addStretch(1)
        lay.addLayout(row)
        self.details = QPlainTextEdit(self)
        self.details.setReadOnly(True)
        self.details.setPlaceholderText(self.tr("Select a run to see its inputs, settings, results and versions."))
        lay.addWidget(self.details, 1)

    def selected_run(self):
        item = self.runs_table.item(self.runs_table.currentRow(), 0)
        return item.data(Qt.UserRole) if item else None

    def _selected(self):
        run_id = self.selected_run()
        self.rerun_button.setEnabled(run_id is not None)
        if run_id is not None:
            self.run_selected.emit(run_id)

    def show_run(self, run):
        """Everything recorded about a run, as text (long results are cut)."""
        import json

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
