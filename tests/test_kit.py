"""UI-3: the component kit (one test per component; NumberField: keystroke check, Enter, Esc, wheel only with
focus, Shift / Ctrl steps, auto, binding)."""

import pytest

pytest.importorskip("PySide6")
from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from astrowb.ui.kit.fields import NumberField  # noqa: E402


def _wheel(field, modifiers=Qt.NoModifier):
    event = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, 120), Qt.NoButton, modifiers,
                        Qt.NoScrollPhase, False)  # fmt: skip
    QApplication.sendEvent(field, event)


def test_number_field_typing_enter_escape(qtbot):
    f = NumberField(5.0, 1, 50, step=0.5, decimals=1, unit="px")
    qtbot.addWidget(f)
    f.show()
    f.setFocus()
    f.lineEdit().selectAll()
    qtbot.keyClicks(f.lineEdit(), "0.5")
    assert f.property("invalid") and "1.0" in f.toolTip() and f.value() == 5.0  # below the range: reason shown
    qtbot.keyClick(f, Qt.Key_Escape)
    assert f.lineEdit().text() == "5.0 px" and not f.property("invalid")
    f.lineEdit().selectAll()
    qtbot.keyClicks(f.lineEdit(), "12")
    assert f.value() == 5.0  # not committed while typing
    qtbot.keyClick(f, Qt.Key_Return)
    assert f.value() == 12.0


def test_number_field_wheel_and_steps(qtbot):
    f = NumberField(5.0, 0, 100, step=1.0, decimals=2)
    qtbot.addWidget(f)
    f.show()
    _wheel(f)
    assert f.value() == 5.0  # no focus: the wheel scrolls the panel
    f.setFocus()
    qtbot.waitUntil(f.hasFocus)
    _wheel(f)
    assert f.value() == 6.0
    qtbot.keyClick(f, Qt.Key_Up, Qt.ShiftModifier)
    assert f.value() == 16.0
    qtbot.keyClick(f, Qt.Key_Up, Qt.ControlModifier)
    assert f.value() == pytest.approx(16.1)


def test_number_field_auto_and_binding(qtbot):
    from astrowb.core.state import Store
    from astrowb.ui.kit.binding import bind

    f = NumberField(3.0, 0, 10, allow_auto=True)
    qtbot.addWidget(f)
    seen = []
    f.auto_changed.connect(seen.append)
    f.set_auto(True, shown=4.2)
    assert f.is_auto() and f.auto_action.isChecked() and f.lineEdit().text().startswith("4.2") and seen == [True]
    f.stepBy(1)  # a change by the user turns auto off
    assert not f.is_auto() and seen == [True, False] and f.value() == 4.0
    store = Store("test")
    bind(f, store, "r", "radius")
    f.setValue(7.0)
    assert store.get("r") == 7.0


def test_info_banner_and_badge(qtbot):
    from astrowb.ui.kit.banners import Badge, InfoBanner

    clicked, gone = [], []
    b = InfoBanner("attention", "3 frames have no time stamp", [("Show them", lambda: clicked.append(1))])
    qtbot.addWidget(b)
    b.dismissed.connect(lambda: gone.append(1))
    b.show()
    b.buttons[0].click()
    b.close_button.click()
    assert clicked == [1] and gone == [1] and not b.isVisible() and b.text().startswith("3 frames")
    assert Badge("calibrated", "ok").text() == "calibrated"
    with pytest.raises(ValueError):
        InfoBanner("loud", "x")


def test_toast(qtbot):
    from PySide6.QtWidgets import QWidget

    from astrowb.ui.kit import toast as T

    win = QWidget()
    qtbot.addWidget(win)
    win.resize(400, 300)
    win.show()
    done = []
    first = T.Toast.show_in(win, "Saved", ("Show in folder", lambda: done.append(1)))
    t = T.Toast.show_in(win, "Saved again")  # replaces the first
    qtbot.waitUntil(lambda: len(win.findChildren(T.Toast)) == 1)
    assert t.geometry().right() == 400 - T.MARGIN - 1 and t.label.text() == "Saved again" and first is not t
    t.timer.setInterval(10)
    t.timer.start()
    qtbot.waitUntil(lambda: not win.findChildren(T.Toast))


def test_segmented(qtbot):
    from astrowb.core.state import Store
    from astrowb.ui.kit.binding import bind
    from astrowb.ui.kit.fields import Segmented

    s = Segmented([("bjd", "BJD"), ("phase", "Phase"), ("ut", "UT")])
    qtbot.addWidget(s)
    seen = []
    s.changed.connect(seen.append)
    assert s.value() == "bjd"
    s.buttons["phase"].click()
    assert s.value() == "phase" and seen == ["phase"] and not s.buttons["bjd"].isChecked()
    store = Store("test")
    bind(s, store, "time", "time axis")
    s.buttons["ut"].click()
    assert store.get("time") == "ut"
    store.set("time", "bjd")
    assert s.value() == "bjd"


def test_empty_state(qtbot):
    from astrowb.ui.kit.empty import EmptyState

    hits = []
    e = EmptyState("open", "No images yet", "Open FITS files.", ("Open images…", lambda: hits.append("open")),
                   sample=lambda: hits.append("sample"))  # fmt: skip
    qtbot.addWidget(e)
    assert [b.text() for b in e.buttons] == ["Open images…", "Try with practice data"] and e.buttons[0].isDefault()
    for b in e.buttons:
        b.click()
    assert hits == ["open", "sample"]


def test_splitter_remembers_and_resets(qtbot):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel

    from astrowb.ui.kit.splitter import Splitter

    class Mem(dict):
        def set(self, k, v):
            self[k] = v

    mem = Mem()

    def make():
        s = Splitter(Qt.Horizontal, mem, "test.main")
        qtbot.addWidget(s)
        s.addWidget(QLabel("a"))
        s.addWidget(QLabel("b"))
        s.resize(400, 100)
        s.show()
        s.setSizes([100, 300])
        s.restore()
        return s

    s = make()
    s.moveSplitter(250, 1)  # the user drags the handle
    assert mem["split.test.main"][0] == 250
    again = make()
    assert again.sizes()[0] == 250  # remembered
    qtbot.mouseDClick(again.handle(1), Qt.LeftButton)
    assert abs(again.sizes()[0] - 100) <= 2 and mem["split.test.main"] == again.sizes()  # the handle's width aside


def test_inspector(qtbot):
    from astrowb.ui.kit.inspector import Inspector

    panel = Inspector("Star")
    qtbot.addWidget(panel)
    panel.set_rows([("Flux", 12345.6, "ADU"), ("Name", "V1234 Cyg")])
    panel.set_rows([("Flux", 12345.6, "ADU"), ("FWHM", 3.2, "px")])  # replaces the rows
    assert panel.form.rowCount() == 2 and panel.copy_text() == "Flux\t12345.6\tADU\nFWHM\t3.2\tpx"
    panel.copy_button.click()
    from PySide6.QtWidgets import QApplication

    assert QApplication.clipboard().text() == panel.copy_text()


def test_dialog(qtbot):
    from PySide6.QtCore import Qt

    from astrowb.ui.kit.dialogs import Dialog

    class Mem(dict):
        def set(self, k, v):
            self[k] = v

    mem = Mem()
    d = Dialog("Export options", None, mem, "export")
    qtbot.addWidget(d)
    yes = d.add_buttons("Export")
    assert yes.isDefault() and d.button_row.itemAt(d.button_row.count() - 1).widget() is yes  # primary last
    d.resize(500, 300)
    d.show()
    qtbot.keyClick(d, Qt.Key_Escape)
    assert d.result() == 0 and mem["dialog.export.size"] == [500, 300]
    again = Dialog("Export options", None, mem, "export")
    qtbot.addWidget(again)
    assert (again.width(), again.height()) == (500, 300)


def test_button_kinds_and_busy(qtbot):
    from astrowb.ui.kit.buttons import Button

    b = Button("Measure", "primary", icon="measure")
    qtbot.addWidget(b)
    assert b.property("primary") and not b.icon().isNull()
    b.set_busy(True)
    assert b.is_busy() and not b.isEnabled() and b.text().endswith("Measure") and b.text() != "Measure"
    b.set_busy(False)
    assert not b.is_busy() and b.isEnabled() and b.text() == "Measure"
    with pytest.raises(ValueError):
        Button("x", "loud")


def test_section(qtbot):
    from astrowb.ui.kit.sections import Section

    asked = []
    s = Section("Apertures", help="photometry-apertures", folded=True, advanced=True)
    qtbot.addWidget(s)
    s.help_requested.connect(asked.append)
    s.help_button.click()
    assert asked == ["photometry-apertures"] and not s.content.isVisibleTo(s) and s.mode == "expert"
    s.button.click()
    assert s.content.isVisibleTo(s)
    assert Section("Plain").help_button is None and Section("Plain").mode is None


def test_form_row(qtbot):
    from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

    from astrowb.ui.kit.fields import NumberField
    from astrowb.ui.kit.forms import LABEL_WIDTH, FormRow

    page = QWidget()
    qtbot.addWidget(page)
    lay = QVBoxLayout(page)
    a = FormRow("Aperture radius", NumberField(5, 1, 50), unit="px", help="Radius of the star's circle")
    b = FormRow("A much longer label that wraps", NumberField(1, 0, 9))
    lay.addWidget(a)
    lay.addWidget(b)
    page.show()
    assert not a.is_changed() and a.dot.text() == ""
    a.control.setValue(8)
    assert a.is_changed() and a.dot.isEnabled()
    a.dot.click()
    assert a.control.value() == 5 and not a.is_changed()
    assert a.label.width() == b.label.width() == LABEL_WIDTH
    from PySide6.QtCore import QPoint

    assert a.control.mapTo(page, QPoint()).x() == b.control.mapTo(page, QPoint()).x()  # one left edge
    assert isinstance(a.layout(), QHBoxLayout) and FormRow("x", NumberField(), reset=False).dot is None


def test_path_field(qtbot, tmp_path):
    from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
    from PySide6.QtGui import QDropEvent

    from astrowb.ui.kit.fields import PathField

    class Mem(dict):
        def set(self, k, v):
            self[k] = v

    files = [tmp_path / f"light_V_{i:03d}.fits" for i in range(48)]
    for f in files:
        f.write_bytes(b"")
    mem = Mem()
    field = PathField("files", "FITS (*.fits)", "test.frames", mem)
    qtbot.addWidget(field)
    seen = []
    field.changed.connect(seen.append)
    data = QMimeData()
    data.setUrls([QUrl.fromLocalFile(str(f)) for f in files])
    drop = QDropEvent(QPointF(5, 5), Qt.CopyAction, data, Qt.LeftButton, Qt.NoModifier)
    field.dropEvent(drop)
    assert len(field.paths()) == 48 and "48" in field.edit.text() and "light_V_000.fits" in field.edit.text()
    assert len(seen) == 1 and mem["recent.test.frames"][0] == field.paths()
    field.set_paths([str(tmp_path / "gone.fits")])
    assert "gone.fits" in field.edit.toolTip() and field.edit.styleSheet()  # amber, with the reason
    field._recent_menu()
    field.button.menu().actions()[0].trigger()  # the recent choice comes back
    assert len(field.paths()) == 48 and field.edit.styleSheet() == ""
    one = PathField("file")
    qtbot.addWidget(one)
    qtbot.keyClicks(one.edit, str(files[0]))
    assert one.paths() == [str(files[0])] and one.kit_binding()[1]() == str(files[0])


def test_kit_gallery_builds(qtbot):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "tools" / "kit_gallery.py"
    spec = importlib.util.spec_from_file_location("kit_gallery", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _app, page = module.gallery()
    qtbot.addWidget(page)
    page.show()
    assert page.findChildren(type(page)) and not page.grab().isNull()


def test_stage_rail_and_panel(qtbot):
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication, QLabel

    from astrowb.ui.kit import rail as R
    from astrowb.ui.kit.buttons import Button

    r = R.StageRail([("images", "Images"), ("stars", "Stars"), ("measure", "Measure")])
    qtbot.addWidget(r)
    r.show()
    chosen = []
    r.stage_chosen.connect(chosen.append)
    r.set_state("images", "done")
    r.buttons["stars"].click()
    assert chosen == ["stars"] and r.width() == R.NARROW and r.buttons["images"].text() == "1 ✓"
    assert r.buttons["stars"].text() == "2 ●" and r.buttons["stars"].isChecked()
    QApplication.sendEvent(r, QEvent(QEvent.Enter))
    assert r.width() == R.NARROW and r.buttons["measure"].toolTip() == "Measure"  # hover: names in the tooltips
    pinned = []
    r.pinned_changed.connect(pinned.append)
    r.pin.click()
    QApplication.sendEvent(r, QEvent(QEvent.Leave))
    assert r.width() == R.WIDE and r.buttons["measure"].text().endswith("Measure") and pinned == [True]
    p = R.StagePanel("Stars", help="photometry-choosing-images-stars")
    qtbot.addWidget(p)
    p.add(QLabel("a row"))
    p.set_primary(Button("Measure", "primary"))
    p.set_primary(Button("Measure again", "primary"))  # replaces
    p.set_status("12 stars chosen")
    assert p.bottom.count() == 1 and p.primary.text() == "Measure again" and p.status.text() == "12 stars chosen"


def test_tool_button_choice_toggle(qtbot):
    from astrowb.core.state import Store
    from astrowb.ui.kit.binding import bind
    from astrowb.ui.kit.buttons import ToolButton
    from astrowb.ui.kit.fields import ChoiceField, Toggle

    t = ToolButton("zoom_in", "Zoom in", shortcut="Ctrl+=", checkable=True)
    qtbot.addWidget(t)
    assert not t.icon().isNull() and t.toolTip().startswith("Zoom in (") and t.isCheckable()
    c = ChoiceField([("young1994", "Young (1994)"), ("secz", "sec z")], "secz")
    qtbot.addWidget(c)
    assert c.value() == "secz"
    store = Store("test")
    bind(c, store, "airmass", "airmass formula")
    c.setValue("young1994")
    assert store.get("airmass") == "young1994"
    with pytest.raises(ValueError):
        c.setValue("nope")
    assert Toggle("Subtract the sky", True).isChecked()


def test_status_segments(qtbot):
    from astrowb.ui.kit.status import StatusSegments

    bar = StatusSegments()
    qtbot.addWidget(bar)
    bar.show()
    stopped = []
    assert not bar.progress.isVisible()
    bar.set_readout("x 1024.3  y 512.7")
    bar.set_progress(62, cancel=lambda: stopped.append(1))
    assert bar.progress.isVisible() and bar.progress.value() == 62 and bar.cancel.isVisible()
    bar.cancel.click()
    bar.set_progress(-1)
    assert stopped == [1] and bar.progress.maximum() == 0 and not bar.cancel.isVisible()
    bar.set_progress(None)
    bar.message("Saved")
    assert not bar.progress.isVisible() and bar.currentMessage() == "Saved" and bar.readout.text().startswith("x")


def test_error_dialog(qtbot):
    from PySide6.QtWidgets import QApplication

    from astrowb.ui.kit.dialogs import ErrorDialog

    reported = []
    d = ErrorDialog(None, "Task failed", "Photometry stopped", "Check the apertures.", "Traceback …",
                    report=lambda: reported.append(1))  # fmt: skip
    qtbot.addWidget(d)
    d.show()
    copy = next(b for b in d.buttons() if b.text() == "Copy")
    copy.click()
    assert QApplication.clipboard().text().startswith("Task failed") and d.isVisible()  # copying keeps it open
    d.report_button.click()
    assert reported == [1] and d.detailedText() == "Traceback …"


def test_window_moved_back_onto_a_screen(qtbot):
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QMainWindow

    from astrowb.ui.kit.window import on_screen

    w = QMainWindow()
    qtbot.addWidget(w)
    room = QGuiApplication.primaryScreen().availableGeometry()
    w.resize(400, 300)
    w.move(room.right() + 5000, room.bottom() + 5000)  # where a removed monitor was
    assert on_screen(w)
    assert room.contains(w.geometry().topLeft())
    assert not on_screen(w)  # already on a screen: left alone


def test_plot_canvas_says_why_it_is_empty(qtbot):
    """UI-6: an empty plot shows words, not a blank rectangle; they go once something is drawn."""
    from astrowb.ui.kit.widgets import PlotCanvas

    plot = PlotCanvas()
    qtbot.addWidget(plot)
    plot.resize(500, 300)
    plot.show()
    assert plot.is_empty() and plot.hint.isVisible() and plot.hint.text()
    plot.set_empty_hint("Choose a star to see its light curve")
    ax = plot.figure.add_subplot()
    assert plot.hint.isVisible()  # axes alone are still empty
    ax.plot([1, 2, 3], [3, 1, 2])
    plot.canvas.draw()
    assert not plot.is_empty() and not plot.hint.isVisible()
    ax.clear()
    plot.canvas.draw()
    assert plot.hint.isVisible() and plot.hint.text().startswith("Choose a star")


class _FakeTask:
    def __init__(self, tid, name="photometry.measure"):
        self.id, self.name, self.state, self.progress, self.message = tid, name, "running", 0.0, ""
        self.finished, self.cancelled = False, False

    def cancel(self):
        self.cancelled = True


def test_task_chip(qtbot):
    from astrowb.ui.kit import tasks as T

    chip = T.TaskChip(name_of=lambda n: n.split(".")[-1])
    qtbot.addWidget(chip)
    assert not chip.isEnabled() and chip.text() == ""
    a, b = _FakeTask(1), _FakeTask(2, "spectro.reduce")
    chip.update_task(a)
    chip.update_task(b)
    assert chip.text() == "2" and chip.isEnabled()
    a.progress = 0.02
    assert "left" not in chip.row_text(a, now=chip.started[1] + 10)  # no estimate before 5 %
    a.progress = 0.25
    assert chip.row_text(a, now=chip.started[1] + 10).endswith("about 30 s left")
    chip._fill()
    first = chip.menu().actions()[0].menu()
    first.actions()[0].trigger()  # Cancel of a running task
    assert a.cancelled or b.cancelled
    b.state, b.finished = "done", True
    chip.update_task(b)
    assert chip.text() == "1" and chip.row_text(b).endswith("finished")
    reported = []
    chip.report = lambda: reported.append(1)
    a.state, a.finished = "failed", True
    chip.update_task(a)
    chip._fill()
    failed = next(act.menu() for act in chip.menu().actions() if act.menu() is not None)
    failed.actions()[0].trigger()  # a failed task offers Report a problem…
    assert reported == [1]
    assert T.eta(10, 0.5) == 10 and T.eta(10, 0.01) is None
    a.state, a.finished, a.message = "running", False, "measuring"  # the phase in the row (UI-9)
    assert "measuring" in chip.row_text(a)
    b.timeline = [("reading", 1.25), ("measuring", 3.5)]  # a finished task: how long each phase took (ARC-17)
    chip._fill()
    done = next(act.menu() for act in chip.menu().actions() if act.menu() and "finished" in act.text())
    assert [x.text() for x in done.actions()] == ["reading: 1.2 s", "measuring: 3.5 s"]


def test_area_window_task_chip_and_toast(qtbot, tmp_path):
    from PySide6.QtWidgets import QLabel

    from astrowb.settings import Settings
    from astrowb.ui.kit.toast import Toast
    from astrowb.ui.kit.window import AreaWindow

    win = AreaWindow("demo", "Demo", Settings(tmp_path), QLabel("main"))
    qtbot.addWidget(win)
    win.show()
    task = _FakeTask(7)
    win.track(task)
    assert win.task_chip.text() == "1"
    task.state, task.finished, task.progress = "done", True, 1.0
    win.task_update(task)
    assert win.task_chip.text() == "" and win.findChildren(Toast)


def test_every_help_anchor_used_exists():
    """UI-7 item 1: a section's or stage's help="…" names a guide topic that exists (in every language)."""
    import re
    from pathlib import Path

    from astrowb.ui import guide_page

    root = Path(__file__).resolve().parents[1]
    used = set()
    for path in [*(root / "src" / "astrowb").rglob("*.py"), root / "tools" / "kit_gallery.py"]:
        used |= set(re.findall(r'\bhelp=["\']([a-z0-9]+(?:-[a-z0-9]+)+)["\']', path.read_text(encoding="utf-8")))
    known = guide_page.anchors("en")
    assert used and not used - set(known), used - set(known)


def test_no_long_explanations_in_working_panels():
    """UI-7 item 3: a label in a working panel is at most 140 characters; the explanation lives in the guide (a
    "More…" link). Kept: Spectroscopy's "In what order?", which the owner asked to see in the window."""
    import re
    from pathlib import Path

    kept = {"1. Raw frames from your spectrograph"}
    long = []
    for path in (Path(__file__).resolve().parents[1] / "src" / "astrowb" / "ui").rglob("*.py"):
        src = path.read_text(encoding="utf-8")
        for m in re.finditer(r'(?:QLabel|help_line)\(\s*(?:self\.tr|translate\([^,]+,)\(\s*((?:"[^"]*"\s*)+)', src):
            text = "".join(re.findall(r'"([^"]*)"', m.group(1)))
            if len(text) > 140 and not any(text.startswith(k) for k in kept):
                long.append(f"{path.name}: {text[:60]}")
    assert not long, long


def test_help_line_opens_the_topic(qtbot, tmp_path):
    from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

    from astrowb.settings import Settings
    from astrowb.ui.kit.help import help_line
    from astrowb.ui.kit.window import AreaWindow

    body = QWidget()
    line = help_line("Radii in pixels.", "photometry-apertures", body)
    QVBoxLayout(body).addWidget(line)
    win = AreaWindow("demo", "Demo", Settings(tmp_path), body)
    qtbot.addWidget(win)
    win.show()
    assert len(line.text()) < 200 and isinstance(line, QLabel)
    line.linkActivated.emit("photometry-apertures")
    assert win.docks["help"].isVisible() and "Apertures" in win.help_panel.title.text()


def test_plot_canvas_right_click_menu(qtbot):
    """UI-10: every plot has Show all, Copy picture, Copy data, Save data… on the right click."""
    from PySide6.QtWidgets import QApplication

    from astrowb.ui.kit.widgets import PlotCanvas

    plot = PlotCanvas()
    qtbot.addWidget(plot)
    ax = plot.figure.add_subplot()
    ax.plot([1, 2, 3], [3, 1, 2], label="V")
    ax.set_xlim(1.5, 2)
    from matplotlib.backend_bases import KeyEvent

    plot.canvas.callbacks.process("key_press_event", KeyEvent("key_press_event", plot.canvas, "a"))  # the a key
    assert ax.get_xlim()[0] < 1.5
    assert plot.copy_data() == 3 and QApplication.clipboard().text().splitlines()[1].endswith("\t3.0")
    plot.copy_picture()
    assert not QApplication.clipboard().pixmap().isNull()
    names = [a.text() for a in plot.context_menu().actions()]
    assert "Copy data" in names and "Save data…" in names and "Show all" in names


def test_empty_plots_say_what_is_running(qtbot, tmp_path):
    """UI-6: while a window's task runs, its empty plots name the task and its progress; then their hint again."""
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    from astrowb.settings import Settings
    from astrowb.ui.kit.widgets import PlotCanvas
    from astrowb.ui.kit.window import AreaWindow

    body = QWidget()
    plot = PlotCanvas(body)
    QVBoxLayout(body).addWidget(plot)
    plot.set_empty_hint("Measure to see the light curve")
    win = AreaWindow("demo", "Demo", Settings(tmp_path), body)
    qtbot.addWidget(win)
    task = _FakeTask(3, "photometry.measure")
    task.progress = 0.4
    win.track(task)
    assert plot.hint.text().startswith("Working:") and "40 %" in plot.hint.text()
    task.state, task.finished = "done", True
    win.task_update(task)
    assert plot.hint.text() == "Measure to see the light curve"


def test_legend_click_hides_and_shows_a_series(qtbot):
    """UI-10: a click on a legend entry hides its series and shows it again, on every plot."""
    from types import SimpleNamespace

    from astrowb.ui.kit.widgets import PlotCanvas

    plot = PlotCanvas()
    qtbot.addWidget(plot)
    ax = plot.figure.add_subplot()
    ax.plot([1, 2], [1, 2], label="V")
    ax.scatter([1, 2], [2, 1], label="comparison")
    ax.legend()
    plot.canvas.draw()
    handles = {text.get_text(): handle for handle, (_t, text) in plot._legend_map.items()}
    assert set(handles) == {"V", "comparison"}
    plot._legend_picked(SimpleNamespace(artist=handles["V"]))
    assert not ax.get_lines()[0].get_visible()
    plot._legend_picked(SimpleNamespace(artist=handles["V"]))
    assert ax.get_lines()[0].get_visible()


def test_a_plot_that_cannot_be_drawn_says_why(qtbot, monkeypatch):
    """UI-6: an error while drawing is shown over the plot (and logged), not a blank rectangle."""
    from astrowb.ui.kit.widgets import PlotCanvas

    plot = PlotCanvas()
    qtbot.addWidget(plot)
    plot.show()
    ax = plot.figure.add_subplot()
    ax.plot([1, 2], [3, 4])
    real = plot.figure.draw
    monkeypatch.setattr(plot.figure, "draw", lambda *a: (_ for _ in ()).throw(ValueError("bad axis limits")))
    plot.canvas.draw()
    assert plot.hint.isVisible() and "bad axis limits" in plot.hint.text()
    monkeypatch.setattr(plot.figure, "draw", real)
    plot.canvas.draw()
    assert not plot.hint.isVisible() and plot.failed is None


def test_showing_a_control_in_a_tab_keeps_the_plots_beside_it_working(qtbot):
    """VAL-8 found it: Show me on a control of a tab dropped the Python objects of the plot's toolbar there (PySide,
    setCurrentWidget on a passing wrapper), and the next fit failed to draw."""
    from PySide6.QtWidgets import QPushButton, QSplitter, QTabWidget

    from astrowb.ui.kit.guided import GuidedBar
    from astrowb.ui.kit.widgets import PlotCanvas

    tabs = QTabWidget()
    qtbot.addWidget(tabs)
    split = QSplitter(tabs)
    button, plot = QPushButton("Fit", split), PlotCanvas(split)
    tabs.addTab(QPushButton("other"), "first")
    tabs.addTab(split, "second")
    GuidedBar._bring_forward(button)
    assert tabs.currentIndex() == 1
    plot.figure.clear()  # raised "Internal C++ object (QAction) already deleted"
