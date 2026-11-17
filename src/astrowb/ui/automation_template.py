"""Automation window: "Save as template" (plans/interface.md UI-16.12)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QInputDialog, QPushButton

from ..engine import automation
from .messages import translate as message

translate = QCoreApplication.translate


def add_template_button(page):
    """The button goes under the automations' New / Save as… row."""
    b = page.template_button = QPushButton(translate("AutomationTemplate", "Save as template"), page)
    b.setToolTip(translate("AutomationTemplate", "Keeps the automation as a template in the list"))
    b.clicked.connect(lambda: save_template_dialog(page))
    left = page.list.parentWidget().layout()
    left.insertWidget(left.count(), b)


def save_template_dialog(page):
    name, ok = QInputDialog.getText(
        page, translate("AutomationTemplate", "Save as template"), translate("AutomationTemplate", "Name:")
    )
    if ok and name.strip():
        save_template(page, name.strip())


def save_template(page, name):
    try:
        path = automation.save_template(page.auto, name, page.lang)
    except ValueError as e:
        page.status.setText(message(e))
        return None
    page.refresh(str(path))
    return path
