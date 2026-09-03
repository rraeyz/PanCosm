"""The frame shared by every area window (plans/interface.md I2.1)."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QUndoCommand, QUndoStack
from PySide6.QtWidgets import QLabel

from astrowb.settings import Settings
from astrowb.ui.area_window import AreaWindow


def _area(qtbot, settings, stack=None):
    act = QAction("Measure")
    win = AreaWindow(
        "test",
        "Test area",
        settings,
        QLabel("view"),
        steps=QLabel("steps"),
        panels=[
            ("stars", "Stars", QLabel("stars"), Qt.RightDockWidgetArea),
            ("plot", "Plot", QLabel("plot"), Qt.BottomDockWidgetArea),
        ],  # fmt: skip
        menus=[("Measure", [act])],
        toolbar=[act],
        undo_stack=stack,
    )
    win._keep = act
    qtbot.addWidget(win)
    win.show()
    return win


def test_a_moved_panel_comes_back_where_it_was_and_reset_puts_it_back(qtbot, tmp_path):
    settings = Settings(tmp_path)
    win = _area(qtbot, settings)
    assert win.dockWidgetArea(win.docks["stars"]) == Qt.RightDockWidgetArea
    win.addDockWidget(Qt.LeftDockWidgetArea, win.docks["stars"])  # the user drags it to the other side
    win.close()
    again = _area(qtbot, settings)
    assert again.dockWidgetArea(again.docks["stars"]) == Qt.LeftDockWidgetArea
    again.reset_layout()
    assert again.dockWidgetArea(again.docks["stars"]) == Qt.RightDockWidgetArea
    again.docks["plot"].setFloating(True)  # pulled out as a window of its own (e.g. a second monitor)
    again.reset_layout()
    assert not again.docks["plot"].isFloating()


def test_menus_undo_view_window_and_screen(qtbot, tmp_path):
    stack = QUndoStack()
    win = _area(qtbot, Settings(tmp_path), stack)
    titles = [a.text() for a in win.menuBar().actions()]
    assert titles == ["&File", "&Edit", "&View", "Measure", "&Window", "&Help"]
    view = [a.text() for a in win.view_menu.actions() if a.text()]
    assert {"Steps", "Stars", "Plot", "Toolbar", "&Reset layout"} <= set(view)
    done = []

    class Cmd(QUndoCommand):
        def redo(self):
            done.append(1)

        def undo(self):
            done.pop()

    stack.push(Cmd("mark a star"))
    assert done == [1] and win.undo_action.isEnabled()
    win.undo_action.trigger()
    assert done == [] and win.redo_action.isEnabled()
    win._fill_window_menu()
    assert "Test area" in [a.text() for a in win.window_menu.actions()]
    with qtbot.waitSignal(win.help_requested) as sig:
        next(a for a in win.help_menu.actions() if a.text() == "Guide for this window").trigger()
    assert sig.args == ["test"]
    assert win.width() <= 1366 and win.height() <= 768
    assert win.minimumSizeHint().width() <= 1366
