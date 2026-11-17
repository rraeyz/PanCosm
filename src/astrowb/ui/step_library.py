"""The step library of the Automation window: every step, to drag onto the chain (UI-16.12)."""

from PySide6.QtCore import QCoreApplication, QMimeData, Qt
from PySide6.QtWidgets import QListWidget

from ..engine import steps
from .names import step_name

STEP_MIME = "application/x-astrowb-step"


class StepLibrary(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        steps.get("fits.save_as")  # loads the built-in steps and plugins
        for sid in sorted(steps.REGISTRY, key=step_name):
            self.addItem(step_name(sid))
            self.item(self.count() - 1).setData(Qt.UserRole, sid)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragOnly)
        self.setToolTip(QCoreApplication.translate("StepLibrary", "Drag a step onto the chain to add it there"))

    def mimeData(self, items):
        mime = QMimeData()
        mime.setData(STEP_MIME, items[0].data(Qt.UserRole).encode())
        return mime
