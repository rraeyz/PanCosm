"""A titled group of the component kit that folds (plans/interface.md "The component kit", UI-3), built on the
existing Collapsible so the interface mode still opens and folds it.

    s = Section(self.tr("Apertures"), help="photometry-apertures", advanced=True)
    s.body.addWidget(...)
    s.help_requested.connect(window.show_help)      # the help button asks for the guide at that place (HelpPanel, UI-7)
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QToolButton

from .icons import icon
from .widgets import Collapsible


class Section(Collapsible):
    help_requested = Signal(str)

    def __init__(self, title, help=None, folded=False, advanced=False, parent=None):  # noqa: A002 (the plan's name)
        # advanced: folded in Basic mode, open in Expert mode; otherwise the interface mode leaves it alone
        super().__init__(title, parent, expanded=not folded, mode="expert" if advanced else None)
        self.help, self.help_button = help, None
        self.setProperty("help_anchor", help)  # F1 on a control inside opens this topic (kit/help.anchor_for)
        if help:
            self.help_button = QToolButton(self)
            self.help_button.setIcon(icon("help", self, 16))
            self.help_button.setAutoRaise(True)
            self.help_button.setToolTip(self.tr("Help on this part"))
            self.help_button.setAccessibleName(self.tr("Help on this part"))
            self.help_button.clicked.connect(lambda: self.help_requested.emit(self.help))
            row = self.layout()
            row.removeWidget(self.button)
            head = QHBoxLayout()
            head.setContentsMargins(0, 0, 0, 0)
            head.addWidget(self.button, 1)
            head.addWidget(self.help_button)
            row.insertLayout(0, head)
