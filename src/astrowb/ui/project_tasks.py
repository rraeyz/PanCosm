"""The Project window's Tasks tab (UI-16.14): every task of this run of the program, from all windows."""

import time

from astropy.table import Table
from PySide6.QtCore import QCoreApplication, QTimer
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QVBoxLayout, QWidget

from .kit import tasks
from .kit.table import TableView

translate = QCoreApplication.translate


class TasksTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        self.table = TableView(self)
        self.table.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.view.horizontalHeader().setStretchLastSection(True)
        self.table.set_row_actions([(self.tr("Cancel"), self.cancel)])
        lay.addWidget(self.table)
        self.entries = []  # the entry of each table row
        self.timer = QTimer(self)  # running rows tick only while the tab is shown
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
        self.timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.timer.stop()

    def cancel(self, rows):
        for i in rows:
            self.entries[i]["task"].cancel()  # no-op for a finished task

    def refresh(self):
        from .names import step_name

        words = {
            k: translate("TaskChip", v)
            for k, v in {"queued": "waiting", "done": "finished", "failed": "failed", "cancelled": "cancelled"}.items()
        }
        now = time.monotonic()
        self.entries = list(tasks.SEEN)
        rows = [
            (
                e["area"],
                step_name(e["task"].name),
                words.get(e["task"].state, translate("TasksTab", "running")),
                time.strftime("%H:%M:%S", time.localtime(e["wall"])),
                tasks._clock((e["ended"] or now) - e["mono"]),
            )
            for e in self.entries
        ]
        names = (
            translate("TasksTab", "Window"),
            translate("TasksTab", "Task"),
            translate("TasksTab", "State"),
            translate("TasksTab", "Started"),
            translate("TasksTab", "Elapsed"),
        )
        keep = self.table.selected_rows()
        self.table.set_table(Table(rows=rows, names=names, dtype=(str,) * 5))
        self.table.view.clearSelection()
        for i in keep:
            self.table.view.selectRow(i)
