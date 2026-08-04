"""Every control on every page says what it does when the pointer rests on it (not everyone knows the terms)."""

import pytest
from PySide6.QtWidgets import QAbstractButton, QAbstractSpinBox, QComboBox, QDialogButtonBox, QLineEdit, QTabBar

from astrowb.settings import Settings


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def _without_tooltip(page):
    missing = []
    for kind in (QAbstractButton, QComboBox, QAbstractSpinBox, QLineEdit):
        for w in page.findChildren(kind):
            if w.toolTip() or w.objectName().startswith("qt_"):
                continue
            parent = w.parent()
            if isinstance(w, QLineEdit) and isinstance(parent, (QComboBox, QAbstractSpinBox)):
                continue  # the text field inside a combo or spin box
            if isinstance(w, QTabBar) or isinstance(parent, (QTabBar, QLineEdit, QDialogButtonBox)):
                continue  # Qt's own scroll arrows, clear buttons, OK / Cancel
            if type(w).__name__ == "QTableCornerButton":
                continue
            missing.append(f"{type(w).__name__} {getattr(w, 'text', lambda: '')()!r}")
    return missing


def test_every_control_has_a_tooltip(window):
    missing = {key: m for key, (_, page) in window.workspaces.items() if (m := _without_tooltip(page))}
    assert not missing


def test_tooltips_are_translated(qtbot, tmp_path):
    from PySide6.QtWidgets import QApplication

    from astrowb.ui import i18n
    from astrowb.ui.workspaces import CalibratePage

    app = QApplication.instance()
    loaded = i18n.install(app, "tr")
    try:
        page = CalibratePage()
        qtbot.addWidget(page)
        assert "kozmik" in page.cosmics.toolTip()
    finally:
        for t in loaded:
            app.removeTranslator(t)


def test_every_dialog_control_has_a_tooltip(window, tmp_path):
    from astrowb.engine import steps
    from astrowb.ui.blink_dialog import BlinkDialog
    from astrowb.ui.coefficients_dialog import CoefficientsDialog
    from astrowb.ui.exposure_dialog import ExposureDialog
    from astrowb.ui.levels_dialog import LevelsDialog
    from astrowb.ui.moving_dialog import MovingObjectDialog
    from astrowb.ui.observatory_dialog import ObservatoryDialog
    from astrowb.ui.plugin_dialog import PluginDialog
    from astrowb.ui.spectrum_tools import BessDialog
    from astrowb.ui.welcome import WelcomeDialog
    from astrowb.ui.workspaces import AavsoDialog

    settings = Settings(tmp_path)
    observatory = ObservatoryDialog(settings)
    observatory.add_device()
    dialogs = {
        "blink": BlinkDialog(),
        "coefficients": CoefficientsDialog(),
        "exposure": ExposureDialog(settings),
        "levels": LevelsDialog(window.image_page.viewer),
        "moving": MovingObjectDialog(settings),
        "observatory": observatory,
        "plugin": PluginDialog(steps.get("fits.save_as")),
        "bess": BessDialog(),
        "welcome": WelcomeDialog(),
        "aavso": AavsoDialog(2),
    }
    missing = {name: m for name, d in dialogs.items() if (m := _without_tooltip(d))}
    for d in dialogs.values():
        d.deleteLater()
    assert not missing
