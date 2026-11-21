"""The Models window's "Fit history" and "Report" result tabs (plans/interface.md UI-16.6). The history lives in
memory only: one row per fit run of this session; "Restore these values" puts a run's parameters back through the
page's undoable edit. The report is the text the page already shows plus the table caption; nothing is computed."""

import time

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from .kit.table_view import DataTable

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ModelsWindow", "…") calls


def add_history_tabs(win, page):
    """Add the two tabs and wrap page.show_fit so each fit is recorded and the report refreshed."""
    page.fit_history = []
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    history = DataTable()
    history.table.setObjectName("fit_history_table")
    restore = QPushButton(translate("ModelsWindow", "Restore these values"))
    restore.setEnabled(False)
    lay.addWidget(history)
    lay.addWidget(restore)
    page.history_view, page.restore_button = history, restore
    win.add_result_tab("history", translate("ModelsWindow", "Fit history"), box)

    report = QWidget()
    rlay = QVBoxLayout(report)
    rlay.setContentsMargins(0, 0, 0, 0)
    text = QPlainTextEdit()
    text.setReadOnly(True)
    copy = QPushButton(translate("ModelsWindow", "Copy"))
    copy.clicked.connect(lambda: QApplication.clipboard().setText(text.toPlainText()))
    rlay.addWidget(text)
    rlay.addWidget(copy)
    page.report_view, page.report_copy = text, copy
    for w in (*box.findChildren(QWidget), *report.findChildren(QWidget), *page.parameters_view.findChildren(QWidget)):
        w.setFocusPolicy(Qt.NoFocus)  # tabs behind the front one sit off-screen: Tab would jump back up to them
    win.add_result_tab("report", translate("ModelsWindow", "Report"), report)

    def restore_run():
        row = history.table.currentRow()
        key = history.key(row) if row >= 0 else None
        if key is not None:
            page.edit(translate("ModelsWindow", "restored values"), page._fill_values, page.fit_history[key]["params"])

    restore.clicked.connect(restore_run)
    history.row_chosen.connect(lambda _k: restore.setEnabled(True))
    show = page.show_fit

    def show_fit(r):
        show(r)
        page.fit_history.append({"time": time.strftime("%H:%M:%S"), "params": dict(r["params"]), "r": r})
        rows = [[h["time"], translate("ModelsWindow", "Eclipsing binary"), h["r"]["chi2r"], h["r"]["rms"],
                 h["r"]["n"], len(h["r"]["free"])] for h in page.fit_history]  # fmt: skip
        history.set_data([translate("ModelsWindow", "Time"), translate("ModelsWindow", "Model"), "χ²ᵣ",
                          "rms", translate("ModelsWindow", "Points"),
                          translate("ModelsWindow", "Free parameters")], rows,
                         keys=list(range(len(rows))))  # fmt: skip
        _, caption = page.fit_table()
        text.setPlainText(page.status.text() + "\n\n" + caption)

    page.show_fit = show_fit
