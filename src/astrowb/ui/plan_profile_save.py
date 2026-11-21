"""ARC-16: a spin box with "Save to the profile" beside it when its value is not the profile's."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QWidget

from ..core import profiles
from ..settings import Settings

translate = QCoreApplication.translate


def with_save_button(page, spin, section, key, label, unit="", settings=None):
    """The spin box and a small button beside it; the button shows only while the value is not the profile's.
    `label` is the translated name in the tooltip; `settings` makes the Settings (default: page.settings)."""
    settings = settings or (lambda: page.settings)
    box = QWidget(page)
    row = QHBoxLayout(box)
    row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(spin, 1)
    button = QToolButton(box)
    setattr(page, f"{key}_save", button)
    button.setText(translate("PlanProfileSave", "Save to the profile"))
    button.setAutoRaise(True)
    row.addWidget(button)

    def refresh():  # connected to valueChanged only: a profile without a horizon shows it once a value is typed
        stored = profiles.section(settings(), section).get(key)
        if section == "camera" and not stored:  # the camera's 0 means not given
            stored = None
        button.setVisible(stored is None or abs(stored - spin.value()) > 1e-9)
        button.setToolTip(
            translate("PlanProfileSave", "Save {0} as the {1} of profile {2}").format(
                f"{spin.value():g}{unit}", label, profiles.active(settings())
            )
        )

    def save():
        profiles.update(settings(), section, **{key: spin.value()})
        refresh()

    spin.valueChanged.connect(refresh)
    button.clicked.connect(save)
    button.hide()
    return box


def save_box(page, spin, key, label, unit):
    """Photometry's camera fields: the page makes a fresh Settings each time (no shared copy to go stale)."""
    return with_save_button(page, spin, "camera", key, label, unit, Settings)
