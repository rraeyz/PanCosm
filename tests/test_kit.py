"""UI-3: the component kit. NumberField (keystroke check, Enter commits, Esc restores, wheel only with focus,
Shift ×10 / Ctrl ×0.1 steps, auto, binding); InfoBanner, Badge, Toast, Segmented, EmptyState, Splitter."""

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
