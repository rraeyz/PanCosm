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
    monkeypatch.setattr("astrowb.ui.area_window.QMessageBox.warning", lambda *a: warned.append(a[2]))
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
    out = make_report(settings, tmp_path / "report.zip", runs)
    with zipfile.ZipFile(out) as z:
        names = set(z.namelist())
        assert {"error.log", "system.txt", "settings.json", "last_steps.json"} <= names
        assert not [n for n in names if n.endswith((".fits", ".fz", ".png"))]
        text = "".join(z.read(n).decode() for n in names)
        steps = json.loads(z.read("last_steps.json"))
        assert "ValueError: x" in z.read("error.log").decode() and "application " in z.read("system.txt").decode()
    assert home not in text and "/data/owner" not in text and "/x/y.fits" not in text
    assert steps[0]["params"] == {"radius": 5.0, "dark": "dark.fits"} and "inputs" not in steps[0]
    assert json.loads(zipfile.ZipFile(out).read("settings.json"))["photometry.last_folder"] == "2026-11-02"
    win = _area(qtbot, settings)
    monkeypatch.setattr("astrowb.ui.area_window.QMessageBox.information", lambda *a: None)
    assert win.report_problem(tmp_path / "r2.zip") and (tmp_path / "r2.zip").exists()
    assert "Report a problem…" in [a.text() for a in win.help_menu.actions()]


def test_night_theme_and_text_size(qtbot, tmp_path):
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QApplication

    from astrowb.ui import theme

    app = QApplication.instance()
    settings = Settings(tmp_path)
    try:
        c = theme.colors("night")
        for value in c.values():  # no blue or green light in the night theme: red only
            q = QColor(value)
            assert q.red() >= q.green() and q.red() >= q.blue() and q.green() == q.blue()
        settings.set("ui.theme", "night")
        win = _area(qtbot, settings)
        assert win.change_font(1) == 11 and settings.get("ui.font_pt") == 11
        assert "font-size: 11pt" in app.styleSheet() and "#0a0000" in app.styleSheet()
        for _ in range(20):
            win.change_font(1)
        assert theme.font_size(settings) == theme.FONT_MAX  # kept within the tested range
        assert win.change_font(0) == theme.FONT_PT
        settings.set("ui.font_pt", "nonsense")
        assert theme.font_size(settings) == theme.FONT_PT
    finally:
        theme.apply(app, "dark")
