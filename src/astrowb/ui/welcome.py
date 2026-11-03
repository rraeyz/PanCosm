"""First-run welcome: shown once, in English, before the main window. Chooses the language, where the
heavy computations run, and the look. Everything can be changed later in the Settings menu."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QVBoxLayout

from ..brand import BRAND
from . import theme
from .i18n import LANGUAGES, system_language


class WelcomeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Welcome to {BRAND.display_name}")  # first run is always English (owner's rule)
        self.resize(640, 480)  # a starting size; small screens may make it narrower
        lay = QVBoxLayout(self)
        title = QLabel(f"<h2>Welcome to {BRAND.display_name}</h2>", self)
        title.setTextFormat(Qt.RichText)
        lay.addWidget(title)
        intro = QLabel("Three quick choices. You can change them any time in the Settings menu.", self)
        intro.setWordWrap(True)
        intro.setProperty("muted", True)
        lay.addWidget(intro)
        form = QFormLayout()
        self.language = QComboBox(self)
        for code, native in LANGUAGES.items():
            self.language.addItem(native, code)
        self.language.setCurrentIndex(list(LANGUAGES).index(system_language()))
        self.device = QComboBox(self)
        gpu = self._gpu_name()
        self.device.addItem("Automatic — graphics card when it is faster (recommended)", "auto")
        self.device.addItem(f"Graphics card ({gpu})" if gpu else "Graphics card (none found)", "gpu")
        self.device.addItem("Processor (CPU) only", "cpu")
        self.look = QComboBox(self)
        for code, label in (("dark", "Dark"), ("light", "Light")):
            self.look.addItem(label, code)
        self.look.currentIndexChanged.connect(self._preview)
        form.addRow("Language", self.language)
        form.addRow("Computations run on", self.device)
        form.addRow("Look", self.look)
        lay.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok, self)
        ok = buttons.button(QDialogButtonBox.Ok)
        ok.setText("Start")
        ok.setProperty("primary", True)
        buttons.accepted.connect(self.accept)
        lay.addWidget(buttons)

    @staticmethod
    def _gpu_name():
        from .. import compute

        try:
            d = compute.describe()
        except Exception:  # no usable GPU driver: the CPU will be used
            return None
        return d.split("GPU: ", 1)[1].split(" [")[0] if d.startswith("GPU:") else None

    def _preview(self):
        from PySide6.QtWidgets import QApplication

        theme.apply(QApplication.instance(), self.look.currentData())

    def choices(self):
        return {
            "ui.language": self.language.currentData(),
            "compute.device": self.device.currentData(),
            "ui.theme": self.look.currentData(),
        }


def first_run(app, settings, dialog_factory=WelcomeDialog):
    """Show the welcome dialog when the application has never been set up. Returns the choices or None."""
    if settings.get("ui.first_run_done"):
        return None
    dlg = dialog_factory()
    dlg.exec()  # closing the window keeps the defaults shown
    choices = dlg.choices()
    for key, value in choices.items():
        settings.set(key, value)
    settings.set("ui.first_run_done", True)
    return choices
