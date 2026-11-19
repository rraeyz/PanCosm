"""ARC-16: Planning's Lowest altitude, with "Save to the profile" when it differs from the profile's horizon."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QWidget

from ..core import profiles

translate = QCoreApplication.translate


def with_save_button(page, spin):
    """The spin box and a small button beside it; the button shows only while the value is not the profile's."""
    box = QWidget(page)
    row = QHBoxLayout(box)
    row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(spin, 1)
    page.horizon_save = button = QToolButton(box)
    button.setText(translate("PlanProfileSave", "Save to the profile"))
    button.setAutoRaise(True)
    row.addWidget(button)

    def refresh():  # connected to valueChanged only: a profile without a horizon shows it once a value is typed
        stored = profiles.section(page.settings, "site").get("horizon")
        button.setVisible(stored is None or abs(stored - spin.value()) > 1e-9)
        button.setToolTip(
            translate("PlanProfileSave", "Save {0}° as the horizon of profile {1}").format(
                f"{spin.value():g}", profiles.active(page.settings)
            )
        )

    def save():
        profiles.update(page.settings, "site", horizon=spin.value())
        refresh()

    spin.valueChanged.connect(refresh)
    button.clicked.connect(save)
    button.hide()
    return box
