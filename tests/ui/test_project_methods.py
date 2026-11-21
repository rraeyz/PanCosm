"""ARC-11 item 4: the Project window's Methods text… (menu action and page button, dialog with Copy and Save)."""

import pytest
from PySide6.QtWidgets import QApplication

from astrowb.settings import Settings


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def test_methods_action_disabled_without_project_or_runs_then_writes_paragraph(window, tmp_path):
    action, button = window.methods_action, window.project_page.methods_open
    assert not action.isEnabled() and not button.isEnabled() and action.toolTip()
    window.open_project(tmp_path / "p.astroproj")
    assert not action.isEnabled() and "finished" in action.toolTip()
    project = window.engine.project
    project.finish_run(project.start_run("stacking.stack", {}, {}), "failed", error="x")
    window._refresh_files()
    assert not action.isEnabled()
    run = project.start_run("stacking.stack", {}, {"align": "wcs", "method": "median", "rejection": "sigma"})
    project.finish_run(run, "done", {})
    window._refresh_files()
    assert action.isEnabled() and button.isEnabled()
    action.trigger()
    dialog = window.methods_dialog
    assert "combined by their median with sigma rejection" in dialog.view.toPlainText()
    dialog.copy_button.click()
    assert QApplication.clipboard().text() == dialog.view.toPlainText()
    saved = dialog.save(tmp_path / "m.txt")
    assert (tmp_path / "m.txt").read_text().strip() == dialog.text and saved
    dialog.close()
