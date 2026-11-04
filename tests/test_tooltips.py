"""Every control on every page says what it does when the pointer rests on it (not everyone knows the terms)."""

import pytest
from PySide6.QtWidgets import QAbstractButton, QAbstractSpinBox, QComboBox, QLineEdit, QTabBar

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
            if isinstance(w, QTabBar) or isinstance(parent, (QTabBar, QLineEdit)):
                continue  # Qt's own scroll arrows and clear buttons
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
