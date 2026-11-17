"""The profile chooser at the top of Settings → Profiles (plans/architecture.md ARC-16): which profile is active,
a new one (a copy of the active one: usually only the site or the camera differs) and removing one."""

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QWidget,
)

from ..core import profiles

translate = QCoreApplication.translate  # pyside6-lupdate reads translate("ProfileChooser", "…") calls


class ProfileChooser(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.form, self.settings = window, window.settings
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox(self)
        self.new_button = QPushButton(translate("ProfileChooser", "New…"), self)
        self.new_button.setToolTip(translate("ProfileChooser", "A copy of this profile under a new name"))
        self.remove_button = QPushButton(translate("ProfileChooser", "Remove"), self)
        self.remove_button.setToolTip(translate("ProfileChooser", "Forget this profile; the next one becomes active"))
        self.export_button = QPushButton(translate("ProfileChooser", "Export…"), self)
        self.export_button.setToolTip(translate("ProfileChooser", "Write this profile to a file for another computer"))
        self.import_button = QPushButton(translate("ProfileChooser", "Import…"), self)
        self.import_button.setToolTip(translate("ProfileChooser", "Read a profile file; it is added, not made active"))
        for w in (self.combo, self.new_button, self.remove_button, self.export_button, self.import_button):
            lay.addWidget(w)
        self.combo.activated.connect(lambda _i: self.switch(self.combo.currentText()))
        self.new_button.clicked.connect(lambda: self.new())
        self.remove_button.clicked.connect(self.remove_shown)
        self.export_button.clicked.connect(lambda: self.export())
        self.import_button.clicked.connect(lambda: self.import_file())
        self.fill()

    def fill(self):
        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItems(profiles.names(self.settings))
        self.combo.blockSignals(False)
        self.remove_button.setEnabled(self.combo.count() > 1)

    def switch(self, name):
        profiles.switch(self.settings, name)
        self.fill()
        self.refresh_fields()

    def new(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, translate("ProfileChooser", "New profile"),
                                            translate("ProfileChooser", "Name:"))  # fmt: skip
            if not ok:
                return
        name = name.strip()
        if not name or name in profiles.names(self.settings):
            return
        profiles.save_as(self.settings, name)
        self.fill()

    def remove_shown(self):
        """Forget the profile shown (the active one): the next in the list becomes active first."""
        current, *others = profiles.names(self.settings)
        if others:
            self.switch(others[0])
            profiles.remove(self.settings, current)
            self.fill()

    def refresh_fields(self):
        """The form's fields show the active profile (no writes: an empty profile stays empty)."""
        for (part, field), control in self.form.profile_controls.items():
            value = profiles.section(self.settings, part)[field]
            control.blockSignals(True)
            if isinstance(control, QLineEdit):
                control.setText(str(value or ""))
            else:
                control.setValue(float(value or 0))
            control.blockSignals(False)
        self.form._show_scale()

    def export(self, path=None):
        path = path or QFileDialog.getSaveFileName(self, translate("ProfileChooser", "Export profile"),
                                                   f"{profiles.active(self.settings)}.profile.json",
                                                   "Profile (*.profile.json)")[0]  # fmt: skip
        if path:
            try:
                profiles.export_profile(self.settings, path)
            except OSError as e:
                from .messages import save_failed

                return save_failed(self, e)
        return path

    def import_file(self, path=None):
        from .messages import translate as message

        path = path or QFileDialog.getOpenFileName(self, translate("ProfileChooser", "Import profile"), "",
                                                   "Profile (*.json)")[0]  # fmt: skip
        if not path:
            return None
        try:
            name = profiles.import_profile(self.settings, path)
        except ValueError as e:
            QMessageBox.warning(self, translate("ProfileChooser", "Import profile"), message(e))
            return None
        self.fill()
        return name
