"""UI-4: the anatomy of an area window at 1366 x 768 with the results dock at its default; the layout memory."""

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QLabel, QPushButton

from astrowb.settings import Settings
from astrowb.ui.kit import layout_memory
from astrowb.ui.kit.anatomy import Stage
from astrowb.ui.kit.empty import EmptyState
from astrowb.ui.kit.rail import StagePanel
from astrowb.ui.kit.window import AreaWindow


def _demo(qtbot, tmp_path):
    win = AreaWindow("demo", "Demo", Settings(tmp_path), QLabel("image"))
    qtbot.addWidget(win)
    stages = []
    for key in ("images", "stars", "apertures", "measure", "plot", "export"):
        panel = StagePanel(key.title())
        panel.add(QLabel(key))
        button = QPushButton("Run " + key)
        button.setProperty("primary", True)
        panel.set_primary(button)
        stages.append(Stage(key, key.title(), panel))
    win.set_stages(stages)
    win.add_result_tab("plot", "Plot", QLabel("plot"))
    win.add_result_tab("table", "Table", QLabel("table"))
    win.set_inspector(QLabel("details"))
    win.docks["inspector"].hide()  # hidden by default below 1500 px
    win.resize(1366, 768)
    win.show()
    qtbot.waitExposed(win)
    qtbot.waitUntil(lambda: not win._restore_due)
    return win


def test_main_view_keeps_55_percent_and_the_primary_action_shows(qtbot, tmp_path):
    win = _demo(qtbot, tmp_path)
    main = win.centralWidget()
    assert main.width() >= 0.55 * win.width(), main.size()  # the stage rail + panel take the rest
    panel = win.stage_panels["images"]
    button = panel.primary
    assert button.isVisible() and panel.rect().contains(button.mapTo(panel, QPoint(0, 0)))  # never scrolls away


def test_set_main_and_empty_state_and_stale_results(qtbot, tmp_path):
    win = _demo(qtbot, tmp_path)
    empty = EmptyState("open", "No images yet", "Open FITS files.", ("Open", lambda: None))
    win.set_empty_state(empty)
    assert empty.isVisible()
    win.set_main(QLabel("spectrum"))
    assert win._main.text() == "spectrum" and win._stack.currentWidget() is win._main and not empty.isVisible()
    win.set_empty_state(empty)
    assert empty.isVisible()
    win.set_empty_state(None)
    assert win._stack.currentWidget() is win._main
    win.set_result_stale("plot")
    assert win.docks["result_plot"].windowTitle() == "Plot (out of date)"
    win.set_result_stale("plot", False)
    assert win.docks["result_plot"].windowTitle() == "Plot"


def test_layout_is_kept_per_screen_arrangement(qtbot, tmp_path, monkeypatch):
    win = _demo(qtbot, tmp_path)
    win.rail.pin.setChecked(False)
    win.docks["result_plot"].setFloating(True)
    win.docks["result_plot"].move(120, 140)
    win.save_layout()
    win.close()
    again = _demo(qtbot, tmp_path)  # the same screens: the rail and the floating tab come back
    assert not again.rail.pinned and again.docks["result_plot"].isFloating()
    again.close()
    saved = Settings(tmp_path).get("area.demo.layouts")
    assert list(saved) == [layout_memory.arrangement()]
    # another arrangement: the last layout is used, and a tab on a screen that is gone is moved onto one
    monkeypatch.setattr(layout_memory, "arrangement", lambda: "other")
    monkeypatch.setattr(layout_memory, "_off_screen", lambda rect: True)
    third = _demo(qtbot, tmp_path)
    box = third.docks["result_plot"].frameGeometry()
    assert third.docks["result_plot"].isFloating() and QRect(third.pos(), third.size()).intersects(box)
    third.reset_layout()
    assert not third.docks["result_plot"].isFloating()
    third.close()
    # a damaged layout is ignored, not an error
    s = Settings(tmp_path)
    s.set("area.demo.layouts", "junk")
    s.set("area.demo.state", "not base64 state")
    _demo(qtbot, tmp_path).close()


def test_the_shared_tools_menu_stays_before_window_and_takes_a_free_alt_key(qtbot, tmp_path):
    """UI-4 item 3: Tools after the area's menus (also those added later) and before Window; its Alt key is a
    letter no other menu of the bar has; each item opens its dialog."""
    from PySide6.QtGui import QAction

    from astrowb.ui.converter_dialog import ConverterDialog

    win = _demo(qtbot, tmp_path)
    win.add_menus([("&Targets", [QAction("x", win)]), ("F&ocus", [QAction("y", win)])])
    titles = [a.text() for a in win.menuBar().actions()]
    assert titles[-5:] == ["&Targets", "F&ocus", "Too&ls", "&Window", "&Help"], titles  # t and o are taken
    items = [a for a in win.tools_menu.actions() if a.text()]
    assert [a.text() for a in items][0] == "Time and coordinate converter…" and len(items) == 3
    assert all(a.toolTip() for a in items)
    items[0].trigger()
    assert isinstance(win.tool_dialog, ConverterDialog) and win.tool_dialog.isVisible()
    win.tool_dialog.close()
