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
    s = Section("Apertures", help="photometry/apertures", folded=True, advanced=True)
    qtbot.addWidget(s)
    s.help_requested.connect(asked.append)
    s.help_button.click()
    assert asked == ["photometry/apertures"] and not s.content.isVisibleTo(s) and s.mode == "expert"
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
    assert r.width() == R.WIDE and r.buttons["measure"].text().endswith("Measure")
    QApplication.sendEvent(r, QEvent(QEvent.Leave))
    assert r.width() == R.NARROW
    r.pin.click()
    QApplication.sendEvent(r, QEvent(QEvent.Leave))
    assert r.width() == R.WIDE  # pinned
    p = R.StagePanel("Stars", help="photometry/stars")
    qtbot.addWidget(p)
    p.add(QLabel("a row"))
    p.set_primary(Button("Measure", "primary"))
    p.set_primary(Button("Measure again", "primary"))  # replaces
    p.set_status("12 stars chosen")
    assert p.bottom.count() == 1 and p.primary.text() == "Measure again" and p.status.text() == "12 stars chosen"
