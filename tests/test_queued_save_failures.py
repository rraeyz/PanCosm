"""A background step that cannot write its output (folder gone, a file where a folder should be) ends in the
translated error box through run_step; nothing is raised and the task queue does not stay busy."""

import sys
import types

import pytest
from PySide6.QtWidgets import QFileDialog

from astrowb.settings import Settings
from astrowb.ui.kit.dialogs import ErrorDialog
from astrowb.ui.main_window import MainWindow


@pytest.fixture
def env(monkeypatch, tmp_path, qtbot, fits_file):
    boxes, raised = [], []
    monkeypatch.setattr(ErrorDialog, "open", lambda self: boxes.append(self.text()))
    monkeypatch.setattr(sys, "excepthook", lambda *a: raised.append(a))
    win = MainWindow(Settings(tmp_path / "cfg"))
    qtbot.addWidget(win)
    win.current_path = fits_file
    return types.SimpleNamespace(win=win, boxes=boxes, raised=raised, gone=tmp_path / "gone", src=fits_file)


def settle(qtbot, env, tasks):
    tasks = tasks if isinstance(tasks, list) else [tasks]
    qtbot.waitUntil(lambda: all(t.finished for t in tasks) and len(env.boxes) >= len(tasks), timeout=20000)
    assert all(t.state == "failed" for t in tasks)
    assert env.raised == []
    assert not env.win.progress.isVisible()
    assert all(b.strip() and "Traceback" not in b for b in env.boxes)


def test_save_as_into_a_missing_folder(env, qtbot):
    settle(qtbot, env, env.win.save_as(env.gone / "x.fits"))


def test_save_as_dialog_and_header_save(env, qtbot, monkeypatch):
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, **k: (str(env.gone / "x.fits"), ""))
    env.win.save_as_dialog()
    task = env.win.save_header_changes({}, [])
    qtbot.waitUntil(lambda: len(env.boxes) >= 2, timeout=20000)
    assert task.state == "failed" and env.raised == []


def test_save_selected_into_a_missing_folder(env, qtbot):
    from astrowb.ui import image_selection

    page = types.SimpleNamespace(selected_paths=lambda: [str(env.src)])
    settle(qtbot, env, image_selection.save_selected(page, env.win, str(env.gone)))


def test_colour_image_into_a_missing_folder(env, qtbot):
    task = env.win.colour_dialog([str(env.src)] * 3, str(env.gone / "c.png"))
    settle(qtbot, env, task)


def test_practice_data_where_a_file_is_in_the_way(env, qtbot, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    settle(qtbot, env, env.win.practice_data(str(blocker / "sub")))
