"""Automation inspector: "on error: stop / skip / continue" of the selected step (plans/interface.md UI-16.12)."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QRadioButton, QWidget

translate = QCoreApplication.translate


class OnErrorBox(QWidget):
    """Three radio buttons; the choice is kept in the step's "on_error" key (absent = stop)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.entry, self.buttons = None, {}
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(translate("AutomationError", "On error:"), self))
        group = QButtonGroup(self)
        for mode, text, tip in (
            ("stop", translate("AutomationError", "stop"), translate("AutomationError", "A failed step ends the run")),
            (
                "skip",
                translate("AutomationError", "skip"),
                translate("AutomationError", "The step is left out; later steps that need its results fail"),
            ),
            (
                "continue",
                translate("AutomationError", "continue"),
                translate("AutomationError", "The run goes on with the next step (the next item of a repeated step)"),
            ),
        ):
            b = QRadioButton(text, self)
            b.setToolTip(tip)
            b.toggled.connect(lambda on, m=mode: on and self._chosen(m))
            group.addButton(b)
            self.buttons[mode] = b
            lay.addWidget(b)
        lay.addStretch(1)

    def show_step(self, entry):
        """Show the settings of `entry` (None: no step selected)."""
        self.entry = None  # the toggles below must not write
        self.setEnabled(entry is not None)
        self.buttons[(entry or {}).get("on_error", "stop")].setChecked(True)
        self.entry = entry

    def _chosen(self, mode):
        if self.entry is not None:
            self.entry.pop("on_error", None) if mode == "stop" else self.entry.__setitem__("on_error", mode)


def show_on_error(page, entry):
    """Show the box of the selected step on the page, under the settings table (made at first use)."""
    if getattr(page, "error_box", None) is None:
        page.error_box = OnErrorBox(page)
        frame = page.settings_table.parentWidget()
        lay = frame.parentWidget().layout()
        lay.insertWidget(lay.indexOf(frame) + 1, page.error_box)
    page.error_box.show_step(entry)
