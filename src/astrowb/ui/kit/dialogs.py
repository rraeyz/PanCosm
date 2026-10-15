"""The few real dialogs (preferences, export options) of the component kit (plans/interface.md "The component kit",
UI-3): buttons on the right with the primary one last, Esc cancels, the size is remembered.

    d = Dialog(self.tr("Export options"), parent, settings, "export")
    d.body.addWidget(...)
    d.add_buttons(self.tr("Export"))            # Cancel, then the primary button; returns the primary
    if d.exec(): ...
"""

from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout


class Dialog(QDialog):
    def __init__(self, title, parent=None, settings=None, key=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.settings, self.key = settings, key
        lay = QVBoxLayout(self)
        self.body = QVBoxLayout()
        lay.addLayout(self.body, 1)
        self.button_row = QHBoxLayout()
        self.button_row.addStretch(1)
        lay.addLayout(self.button_row)
        size = settings.get(f"dialog.{key}.size") if settings is not None and key else None
        if isinstance(size, list) and len(size) == 2:
            self.resize(*size)

    def add_buttons(self, primary, cancel=None):
        """Cancel (Esc) then the primary button (Enter), on the right; the primary accepts the dialog."""
        no = QPushButton(cancel or self.tr("Cancel"), self)
        no.clicked.connect(self.reject)
        yes = QPushButton(primary, self)
        yes.setDefault(True)
        yes.clicked.connect(self.accept)
        self.button_row.addWidget(no)
        self.button_row.addWidget(yes)
        return yes

    def done(self, result):
        if self.settings is not None and self.key:
            self.settings.set(f"dialog.{self.key}.size", [self.width(), self.height()])
        super().done(result)


class ErrorDialog(QMessageBox):
    """The failure of a task (plans/interface.md "The component kit"): what happened, what to do, the details
    folded, Copy and Report.

    ErrorDialog(parent, self.tr("Task failed"), what, todo, details=traceback, report=self.report_problem).open()
    """

    def __init__(self, parent, title, what, todo="", details="", report=None):
        super().__init__(QMessageBox.Warning, title, what, parent=parent)
        self.setInformativeText(todo)
        if details:
            self.setDetailedText(details)  # the full traceback, for reports
        self.full = "\n\n".join(t for t in (title, what, todo, details) if t)
        copy = self.addButton(self.tr("Copy"), QMessageBox.ActionRole)
        copy.clicked.disconnect()  # an action button closes the box by default: copying keeps it open
        copy.clicked.connect(lambda: QApplication.clipboard().setText(self.full))
        self.report_button = None
        if report is not None:
            self.report_button = self.addButton(self.tr("Report…"), QMessageBox.ActionRole)
            self.report_button.clicked.connect(lambda: report())  # not with the clicked flag as an argument
        self.addButton(QMessageBox.Close)
