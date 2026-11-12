"""The frame shared by every area window (plans/interface.md I2.1)."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QUndoCommand, QUndoStack
from PySide6.QtWidgets import QLabel, QWidget

from astrowb.settings import Settings
from astrowb.ui.kit.window import AreaWindow


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


def test_command_search_finds_and_runs_any_action_in_every_language(qtbot, tmp_path):
    win = _area(qtbot, Settings(tmp_path), QUndoStack())
    shown = [text for text, _ in win.commands()]
    assert "View › Reset layout" in shown and "Measure › Measure" in shown and "Help › Guide for this window" in shown
    assert "Edit › Find an action…" not in shown  # not itself
    dialog = win.find_command()
    qtbot.keyClicks(dialog.search, "layout reset")  # words in any order
    assert [dialog.list.item(i).text() for i in range(dialog.list.count())] == ["View › Reset layout"]
    win.addDockWidget(Qt.LeftDockWidgetArea, win.docks["stars"])
    qtbot.keyClick(dialog.search, Qt.Key_Return)
    assert win.dockWidgetArea(win.docks["stars"]) == Qt.RightDockWidgetArea  # Reset layout ran
    from pathlib import Path

    from PySide6.QtCore import QCoreApplication, QTranslator

    import astrowb

    for lang, word in (("tr", "düzeni"), ("de", "anordnung"), ("es", "disposición")):
        tr = QTranslator()
        assert tr.load(str(Path(astrowb.__file__).parent / "resources" / "i18n" / f"app_{lang}.qm"))
        QCoreApplication.installTranslator(tr)
        try:
            local = _area(qtbot, Settings(tmp_path / lang))
            assert any(word in text.casefold() for text, _ in local.commands()), lang
        finally:
            QCoreApplication.removeTranslator(tr)


def test_recent_files_drop_and_sessions(qtbot, tmp_path, monkeypatch):
    from PySide6.QtCore import QMimeData, QPoint, QUrl
    from PySide6.QtGui import QDropEvent

    opened, state = [], {"stars": [[10.0, 20.0]], "radius": 5}
    win = AreaWindow(
        "phot", "Photometry", Settings(tmp_path), QLabel("view"), open_files=opened.extend,
        session=(lambda: dict(state), lambda st: state.update(st)),
    )  # fmt: skip
    qtbot.addWidget(win)
    files = [tmp_path / f"f{i}.fits" for i in range(3)]
    for f in files:
        f.write_text("x")
    win.open_files(files[:2])
    data = QMimeData()
    data.setUrls([QUrl.fromLocalFile(str(files[2]))])
    win.dropEvent(QDropEvent(QPoint(5, 5), Qt.CopyAction, data, Qt.LeftButton, Qt.NoModifier))
    assert opened == [str(f) for f in files]
    assert win.recent()[0] == str(files[2])  # newest first
    win._fill_recent()
    assert [a.text() for a in win.recent_menu.actions()][:3] == ["f2.fits", "f0.fits", "f1.fits"]
    session = tmp_path / "night.session.json"
    win.save_session(session)
    state.update(stars=[], radius=9)
    assert win.open_session(session) is None and state == {"stars": [[10.0, 20.0]], "radius": 5}
    warned = []
    monkeypatch.setattr("astrowb.ui.kit.window.QMessageBox.warning", lambda *a: warned.append(a[2]))
    other = AreaWindow("spectro", "Spectroscopy", Settings(tmp_path / "o"), QLabel("v"), session=(dict, print))
    qtbot.addWidget(other)
    assert "another window" in other.open_session(session) and warned
    (tmp_path / "bad.session.json").write_text("{not json")
    assert "damaged" in win.open_session(tmp_path / "bad.session.json")
    assert not other.acceptDrops() and win.acceptDrops()


def test_report_a_problem_holds_what_is_needed_and_nothing_personal(qtbot, tmp_path, monkeypatch):
    import json
    import zipfile
    from pathlib import Path

    from astrowb.ui.report import make_report

    settings = Settings(tmp_path / "cfg")
    home = str(Path.home())
    settings.set("photometry.last_folder", f"{home}/nights/2026-11-02")
    settings.set("ui.theme", "dark")
    (tmp_path / "cfg" / "error.log").write_text(f'Traceback\n  File "{home}/secret/run.py", line 3\nValueError: x\n')
    error = f"cannot read {home}/nights/a.fits"
    params = {"radius": 5.0, "dark": "/data/owner/dark.fits"}
    runs = [{"step": "photometry.measure", "params": params, "status": "failed", "error": error,
             "inputs": {"images": ["/x/y.fits"]}}]  # fmt: skip
    (tmp_path / "cfg" / "gpu-report.json").write_text(json.dumps({"adapter": {"device": "RTX"}, "jobs": []}))
    from astrowb.core import log, profiles

    profiles.update(settings, "observer", name="Ayşe Gözlemci", aavso_code="AGZ")
    profiles.update(settings, "site", name="Bahçe", lat=39.91234, lon=32.85678)
    (tmp_path / "cfg" / log.NAME).write_text("2026-11-11 10:00:00 INFO astrowb.engine: step started\n")
    out = make_report(settings, tmp_path / "report.zip", runs)
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
        assert {"error.log", "system.txt", "settings.json", "last_steps.json", "gpu-report.json"} <= names
        assert "compiled routines" in z.read("system.txt").decode()
        assert not [n for n in names if n.endswith((".fits", ".fz", ".png"))]
        text = "".join(z.read(n).decode() for n in names)
        steps = json.loads(z.read("last_steps.json"))
        assert "ValueError: x" in z.read("error.log").decode() and "application " in z.read("system.txt").decode()
    assert home not in text and "/data/owner" not in text and "/x/y.fits" not in text
    assert steps[0]["params"] == {"radius": 5.0, "dark": "dark.fits"} and "inputs" not in steps[0]
    sent = json.loads(zipfile.ZipFile(out).read("settings.json"))
    assert sent["photometry.last_folder"] == "2026-11-02"
    assert "Ayşe" not in text and "AGZ" not in text and "Bahçe" not in text  # ARC-17: no names, no codes
    assert sent["profile"]["site"]["lat"] == 39.9 and "step started" in zipfile.ZipFile(out).read("app.log").decode()
    win = _area(qtbot, settings)
    monkeypatch.setattr("astrowb.ui.kit.window.QMessageBox.information", lambda *a: None)
    assert win.report_problem(tmp_path / "r2.zip") and (tmp_path / "r2.zip").exists()
    assert "Report a problem…" in [a.text() for a in win.help_menu.actions()]
    win.session = (lambda: {"images": [f"{home}/nights/a.fits"], "radius": 5}, None)  # ARC-17: the window's state
    win.report_problem(tmp_path / "r3.zip")
    state = json.loads(zipfile.ZipFile(tmp_path / "r3.zip").read("session.json"))
    assert state == {"area": "test", "state": {"images": ["a.fits"], "radius": 5}}


@pytest.mark.slow
def test_text_size(qtbot, tmp_path):
    from PySide6.QtWidgets import QApplication

    from astrowb.ui import theme

    app = QApplication.instance()
    settings = Settings(tmp_path)
    try:
        win = _area(qtbot, settings)
        assert win.change_font(1) == 11 and settings.get("ui.font_pt") == 11
        assert "font-size: 11pt" in app.styleSheet()
        for _ in range(20):
            win.change_font(1)
        assert theme.font_size(settings) == theme.FONT_MAX  # kept within the tested range
        assert win.change_font(0) == theme.FONT_PT
        settings.set("ui.font_pt", "nonsense")
        assert theme.font_size(settings) == theme.FONT_PT
    finally:
        theme.apply(app, "dark")


def test_long_work_shows_progress_and_cancel_in_the_status_bar(qtbot, tmp_path):
    class FakeTask:
        def __init__(self, i):
            self.id, self.name, self.state, self.progress, self.message = i, f"measure {i}", "running", 0.0, ""
            self.finished = self.cancelled = False

        def cancel(self):
            self.cancelled = True

    win = _area(qtbot, Settings(tmp_path))
    a, b = FakeTask(1), FakeTask(2)
    win.track(a)
    assert win.task_progress.isVisible() and win.task_cancel.isVisible()
    a.progress, a.message = 0.42, "frame 42 of 100"
    win.task_update(a)
    assert win.task_progress.value() == 42 and "frame 42 of 100" in win.statusBar().currentMessage()
    win.track(b)
    assert "+1" in win.task_progress.format()
    win.task_cancel.click()
    assert a.cancelled and b.cancelled
    for t in (a, b):
        t.finished, t.state = True, "cancelled"
        win.task_update(t)
    assert not win.task_progress.isVisible() and "cancelled" in win.statusBar().currentMessage()
    win.task_update(FakeTask(9))  # a task of another window: ignored
    assert not win.task_progress.isVisible()


def test_steps_are_shown_by_name_not_by_id():
    """The user reads 'Suggest comparison stars', not 'photometry.suggest_comparisons' (interface I4d); every
    built-in step has a name, a plugin's step keeps its id."""
    from astrowb.engine import steps
    from astrowb.ui.step_names import NAMES, step_name

    steps.get("fits.save_as")  # loads the built-in steps
    builtin = {s for s in steps.REGISTRY if not s.startswith("plugin")}
    assert builtin <= set(NAMES), builtin - set(NAMES)
    assert step_name("photometry.suggest_comparisons") == "Suggest comparison stars"
    assert step_name("myplugin.thing") == "myplugin.thing"


def test_settings_of_the_bundled_automations_are_shown_by_name():
    """The Automation window showed keys ("clock_utc_offset", "← folder"); every setting and input of the steps in
    the bundled templates has a name, the key stays in the tooltip, others show the key with spaces (I6b (5))."""
    import json
    from pathlib import Path

    import astrowb
    from astrowb.engine import steps
    from astrowb.ui.setting_names import setting_name

    unnamed = set()
    for path in (Path(astrowb.__file__).parent / "resources" / "automations").glob("*.json"):
        for entry in json.loads(path.read_text())["steps"]:
            s = steps.get(entry["step"])
            for key in (*s.inputs, *s.optional, *s.defaults):  # AUT-1: every setting and input names itself
                if setting_name(entry["step"], key) == key.replace("_", " "):
                    unnamed.add(key)
    assert not unnamed, unnamed
    assert setting_name("calibration.scan", "folder") == "Folder of the night's frames"  # an input, from engine.io
    assert setting_name("calibration.scan", "clock_utc_offset") == "Camera clock − UTC (h)"
    assert setting_name("stacking.stack", "method") == "Combine"  # from the step's own description
    assert setting_name("myplugin.thing", "my_value") == "my value"


def test_one_icon_set_and_icon_toolbars(qtbot, tmp_path):
    """interface I6c.1: one icon per kind of action, never one icon for two kinds; area toolbars show icons, View →
    Toolbar text adds the names and is kept; the Photometry and Spectroscopy toolbars have an icon for every
    action."""
    from PySide6.QtCore import Qt

    from astrowb.ui.kit.icons import ICONS, icon
    from astrowb.ui.main_window import MainWindow

    assert len(set(ICONS.values())) == len(ICONS)  # no symbol or standard icon serves two kinds
    settings = Settings(tmp_path)
    win = _area(qtbot, settings)
    assert all(not icon(kind, win).isNull() for kind in ICONS)
    win.set_icons({win._keep: "measure"})
    assert not win._keep.icon().isNull() and win.toolbar.toolButtonStyle() == Qt.ToolButtonIconOnly
    win.toolbar_text_action.trigger()
    assert win.toolbar.toolButtonStyle() == Qt.ToolButtonTextBesideIcon and settings.get("ui.toolbar_text")
    assert _area(qtbot, settings).toolbar.toolButtonStyle() == Qt.ToolButtonTextBesideIcon  # kept
    main = MainWindow(Settings(tmp_path / "main"))
    qtbot.addWidget(main)
    try:
        for key in ("photometry", "spectroscopy"):
            main.show_workspace(key)
            acts = main.area_windows[key].area_tools()
            assert acts and all(not a.icon().isNull() and a.toolTip() for a in acts), key
    finally:
        main.engine.shutdown()


def test_area_window_anatomy(qtbot, tmp_path):
    """UI-4 item 1 and 5: stages in a rail with their panels, inspector, result tabs, F9 / F10 / F11 / Ctrl+n."""
    from astrowb.ui.kit.anatomy import Stage

    win = AreaWindow("demo", "Demo", Settings(tmp_path), QLabel("main view"))
    qtbot.addWidget(win)
    win.set_stages([Stage(k, k.title(), QLabel(k), help=f"demo-{k}") for k in ("images", "stars", "measure")])
    win.set_inspector(QLabel("details"))
    win.add_result_tab("plot", "Plot", QLabel("plot"))
    win.add_result_tab("table", "Table", QLabel("table"))
    win.show()
    win.activateWindow()
    qtbot.waitUntil(win.isActiveWindow)
    assert win.current_stage() == "images" and win.stage_stack.currentWidget() is win.stage_panels["images"]
    qtbot.keyClick(win, Qt.Key_2, Qt.ControlModifier)
    assert win.current_stage() == "stars" and win.rail.buttons["stars"].isChecked()
    win.set_stage_state("images", "done")
    assert win.rail.buttons["images"].text().startswith("1 ✓")
    for key, dock in ((Qt.Key_F9, "stages"), (Qt.Key_F10, "inspector")):
        qtbot.keyClick(win, key)
        assert not win.docks[dock].isVisible()
    qtbot.keyClick(win, Qt.Key_F11)
    assert not any(d.isVisible() for d in win._results())
    qtbot.keyClick(win, Qt.Key_F11)
    assert all(d.isVisible() for d in win._results())
    asked = []
    win.help_requested.connect(asked.append)
    win.stage_panels["stars"].help_requested.emit("photometry-apertures")
    assert asked == ["photometry-apertures"]


def test_toolbar_right_end_finds_actions(qtbot, tmp_path):
    """UI-4 item 4: the toolbar ends with Find an action and Help; typing there opens the search with the text."""
    act = QAction("Measure the stars")
    win = AreaWindow("demo", "Demo", Settings(tmp_path), QLabel("main view"), toolbar=[act])
    qtbot.addWidget(win)
    later = QAction("Later action")
    win.add_menus([], toolbar=[later])
    acts = win.toolbar.actions()
    assert acts.index(later) < acts.index(win._end) < acts.index(win.help_action)  # area actions stay left
    asked = []
    win.help_requested.connect(asked.append)
    win.help_action.trigger()
    assert asked == ["demo"] and not win.help_action.icon().isNull()
    win.show()
    qtbot.keyClicks(win.find_field, "m")
    dialog = next(w for w in win.findChildren(QWidget) if type(w).__name__ == "CommandSearch")
    assert dialog.search.text() == "m" and win.find_field.text() == ""


def test_keyboard_shortcuts_sheet_and_no_key_twice(qtbot, tmp_path):
    """UI-12: Help → Keyboard shortcuts lists the window's keys; no window gives one key to two actions."""
    from astrowb.ui.kit.shortcuts import duplicates
    from astrowb.ui.main_window import MainWindow

    win = AreaWindow("demo", "Demo", Settings(tmp_path), QLabel("main"))
    qtbot.addWidget(win)
    sheet = win.show_shortcuts()
    rows = [sheet.table.item(i, 0).text() for i in range(sheet.table.rowCount())]
    assert any("Find an action" in r for r in rows) and any("Keyboard shortcuts" in r for r in rows)
    sheet.search.setText("find action")
    shown = [i for i in range(sheet.table.rowCount()) if not sheet.table.isRowHidden(i)]
    assert shown and all("Find" in sheet.table.item(i, 0).text() for i in shown)
    main = MainWindow(Settings(tmp_path / "main"))
    qtbot.addWidget(main)
    try:
        from astrowb.ui.start_page import areas

        for key, *_ in areas():
            main.show_workspace(key)
            area = main.area_windows.get(key)
            if area is not None:
                assert duplicates(area) == {}, key
        sizes = [a for a in main.actions() if a.shortcut().toString() == "Ctrl+Shift++"]
        assert sizes and sizes[0].shortcutContext() == Qt.WidgetWithChildrenShortcut  # main window keeps the keys
    finally:
        main.engine.shutdown()


def test_f1_opens_the_help_panel_for_the_control_in_focus(qtbot, tmp_path):
    """UI-7 item 2: F1 on a control inside a Section with help opens that guide topic beside the work; elsewhere
    the window's guide as before; "Open the full guide" goes on in the guide."""
    from PySide6.QtWidgets import QLineEdit

    from astrowb.ui.kit.sections import Section

    section = Section("Apertures", help="photometry-apertures")
    field = QLineEdit()
    section.body.addWidget(field)
    win = AreaWindow("demo", "Demo", Settings(tmp_path), section)
    qtbot.addWidget(win)
    asked = []
    win.help_requested.connect(asked.append)
    win.show()
    field.setFocus()
    qtbot.waitUntil(field.hasFocus)
    win.help_action.trigger()
    assert win.docks["help"].isVisible() and "Apertures" in win.help_panel.title.text() and not asked
    assert "aperture" in win.help_panel.text.toPlainText().lower()
    win.help_panel.more.click()
    assert asked == ["photometry-apertures"]
    win.centralWidget().setFocus()
    section.button.setFocus()
    assert not win.show_help("no-such-anchor")


def test_app_log_rotates_and_keeps_the_newest_lines(tmp_path):
    """ARC-17: app.log in the settings folder; tail gives its newest lines."""
    import logging

    from astrowb.core import log

    handler = log.start(tmp_path)
    try:
        assert handler is not None and log.start(tmp_path) is None  # once
        logging.getLogger("astrowb.test").info("hello %d", 42)
        handler.flush()
        assert log.tail(tmp_path, 5).strip().endswith("INFO astrowb.test: hello 42")
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()


def test_cache_note_names_the_oldest_saved_answer(qtbot, tmp_path):
    """ARC-14: a task that used saved online answers says so, with the fetch date that may be out of date."""
    from types import SimpleNamespace

    from PySide6.QtCore import QDateTime

    win = _area(qtbot, Settings(tmp_path))
    assert win.cache_note(SimpleNamespace(sources={"vizier": (1.0e9, False)})) == ""  # fetched now: nothing to say
    old = QDateTime.fromString("2026-11-02 10:00", "yyyy-MM-dd HH:mm").toSecsSinceEpoch()
    note = win.cache_note(SimpleNamespace(sources={"vizier": (old + 86400, True), "simbad": (old, True)}))
    assert "2026-11-02 10:00" in note


def test_f5_runs_the_stage_and_esc_stops_the_work(qtbot, tmp_path):
    """UI-12: F5 presses the stage's main button; Esc cancels running work, and only then (Esc stays for fields)."""
    from types import SimpleNamespace

    from PySide6.QtWidgets import QPushButton

    from astrowb.ui.kit.anatomy import Stage

    win = AreaWindow("demo", "Demo", Settings(tmp_path), QLabel("main view"))
    qtbot.addWidget(win)
    run = QPushButton("Measure")
    run.setProperty("primary", True)
    pressed = []
    run.clicked.connect(lambda: pressed.append(1))
    win.set_stages([Stage("images", "Images", QLabel("none")), Stage("measure", "Measure", run)])
    win.show()
    win.activateWindow()
    qtbot.waitUntil(win.isActiveWindow)
    qtbot.keyClick(win, Qt.Key_F5)
    assert not pressed and "no main action" in win.statusBar().currentMessage()
    win.show_stage("measure")
    qtbot.keyClick(win, Qt.Key_F5)
    assert pressed == [1]
    assert not win.cancel_action.isEnabled()
    stopped = []
    task = SimpleNamespace(id=1, name="photometry.measure", state="running", progress=0.2, message="", finished=False,
                           cancel=lambda: stopped.append(1))  # fmt: skip
    win.track(task)
    qtbot.keyClick(win, Qt.Key_Escape)
    assert stopped == [1]


def test_tile_and_gather_windows(qtbot, tmp_path):
    """UI-14: Window → Tile side by side splits the screen's free area; Bring all … puts a lost window back."""
    from PySide6.QtGui import QGuiApplication

    from astrowb.ui.kit import screens

    a, b = _area(qtbot, Settings(tmp_path / "a")), _area(qtbot, Settings(tmp_path / "b"))
    room = QGuiApplication.primaryScreen().availableGeometry()
    left, right = screens.tile([a, b])
    assert left.x() == room.x() and right.x() == room.x() + room.width() // 2 and left.height() == room.height()
    b.move(room.right() + 5000, room.bottom() + 5000)  # on a monitor that was unplugged
    screens.gather([a, b])
    assert room.contains(b.geometry().topLeft()) and room.contains(a.geometry().topLeft())
    texts = [act.text() for act in (a._fill_window_menu() or a.window_menu.actions())]
    assert "Tile side by side" in texts and "Bring all windows to this screen" in texts


def test_long_work_is_worth_a_desktop_notification(qtbot, tmp_path):
    """UI-9: work longer than a minute ends while the program is behind: a system notification (unless turned off;
    a desktop without a tray simply gets none)."""
    import time
    from types import SimpleNamespace

    from astrowb.ui.kit import notify

    settings = Settings(tmp_path)
    long, short = SimpleNamespace(_started=time.monotonic() - 61), SimpleNamespace(_started=time.monotonic())
    assert notify.worth_it(long, settings) and not notify.worth_it(short, settings)
    assert not notify.worth_it(SimpleNamespace(), settings)  # never started (cancelled while waiting)
    settings.set("ui.notify", False)
    assert not notify.worth_it(long, settings)
    win = _area(qtbot, settings)
    assert notify.notify(win, "Photometry", "Measure: finished") in (True, False)


def test_shift_f1_then_a_click_opens_that_controls_topic(qtbot, tmp_path):
    """UI-7: Help → What is this? (Shift+F1): the next click opens the clicked control's guide topic and does not
    act; Esc ends it with nothing opened."""
    from PySide6.QtWidgets import QPushButton

    from astrowb.ui.kit.sections import Section

    section = Section("Apertures", help="photometry-apertures")
    button = QPushButton("Measure")
    pressed = []
    button.clicked.connect(lambda: pressed.append(1))
    section.body.addWidget(button)
    win = AreaWindow("demo", "Demo", Settings(tmp_path), section)
    qtbot.addWidget(win)
    win.show()
    win.whats_this()
    qtbot.mouseClick(button, Qt.LeftButton)
    assert win.docks["help"].isVisible() and "Apertures" in win.help_panel.title.text() and not pressed
    qtbot.mouseClick(button, Qt.LeftButton)  # the mode lasts one click
    assert pressed == [1]
    win.docks["help"].hide()
    win.whats_this()
    qtbot.keyClick(button, Qt.Key_Escape)
    qtbot.mouseClick(button, Qt.LeftButton)
    assert pressed == [1, 1] and not win.docks["help"].isVisible()


def test_the_main_button_waits_while_its_work_runs(qtbot, tmp_path):
    """UI-9: the stage's main button that started a task is disabled and shows the progress until the task ends."""
    from types import SimpleNamespace

    from PySide6.QtWidgets import QPushButton

    from astrowb.ui.kit.anatomy import Stage

    win = AreaWindow("demo", "Demo", Settings(tmp_path), QLabel("view"))
    qtbot.addWidget(win)
    run = QPushButton("Measure")
    run.setProperty("primary", True)
    win.set_stages([Stage("measure", "Measure", run)])
    win.show()
    run.setFocus()
    qtbot.waitUntil(run.hasFocus)
    task = SimpleNamespace(id=7, name="photometry.measure", state="running", progress=0.0, message="", finished=False,
                           cancel=lambda: None)  # fmt: skip
    win.track(task)
    task.progress = 0.4
    win.task_update(task)
    assert not run.isEnabled() and run.text() == "Measure — 40 %"
    task.state, task.finished = "done", True
    win.task_update(task)
    assert run.isEnabled() and run.text() == "Measure"
