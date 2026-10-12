"""The few real dialogs (preferences, export options) of the component kit (plans/interface.md "The component kit",
UI-3): buttons on the right with the primary one last, Esc cancels, the size is remembered.

    d = Dialog(self.tr("Export options"), parent, settings, "export")
    d.body.addWidget(...)
    d.add_buttons(self.tr("Export"))            # Cancel, then the primary button; returns the primary
    if d.exec(): ...
"""

from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QVBoxLayout


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
