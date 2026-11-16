"""UI-15: every window, in every interface language and both themes, at 1366 × 768: no label or button cuts its
text, no panel scrolls sideways, every button has a name a screen reader can say (ARC-19). tools/ui_gallery.py:
its screenshots are for looking at, this test for the measurements."""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

TOOL = Path(__file__).resolve().parents[1] / "tools" / "ui_gallery.py"


def _gallery():
    spec = importlib.util.spec_from_file_location("ui_gallery", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "linux", reason="measured with the Linux fonts (the plan: CI runs it on Linux)")
def test_no_cut_text_in_any_window(qapp, tmp_path):
    from astrowb.ui.i18n import LANGUAGES

    # GALLERY_OUT: CI sets it and uploads the screenshots and contact sheets as an artifact
    found = _gallery().run(tuple(LANGUAGES), ("dark", "light"), os.environ.get("GALLERY_OUT"), tmp_path)
    assert found and all(key.count("-") >= 2 for key in found)
    cut = {k: v for k, v in found.items() if v}
    assert not cut, cut


@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "linux", reason="measured with the Linux fonts")
def test_no_cut_text_with_texts_40_percent_longer(qapp, tmp_path):
    """ARC-18 item 3: the pseudo-locale (every text 40 % longer, accented) cuts nothing and scrolls nothing sideways."""
    gallery = _gallery()
    assert gallery.pseudo_translator().translate("MainWindow", "Open {n} files") == "Õpéñ {n} fîléš·····"
    found = gallery.run(("pseudo",), ("dark",), settings_dir=tmp_path)
    cut = {k: v for k, v in found.items() if v}
    assert found and not cut, cut


@pytest.mark.slow
@pytest.mark.skipif(sys.platform != "linux", reason="measured with the Linux fonts")
@pytest.mark.parametrize("factor", ["1.25", "1.5", "2"])
def test_no_cut_text_at_other_scale_factors(tmp_path, factor):
    """ARC-19: at 125 %, 150 % and 200 % (Windows' usual settings) nothing is cut either. The factor is read when
    Qt starts, so each runs in a process of its own."""
    import os
    import subprocess

    env = os.environ | {"QT_SCALE_FACTOR": factor, "QT_QPA_PLATFORM": "offscreen"}
    run = subprocess.run([sys.executable, str(TOOL), "--langs", "en", "--themes", "dark", "--out", str(tmp_path)],
                         env=env, capture_output=True, text=True, timeout=600)  # fmt: skip
    assert run.returncode == 0 and run.stdout.strip().endswith("no cut text"), run.stdout[-3000:] + run.stderr[-2000:]


def test_a_long_label_is_found(qtbot):
    """The measurement names the widget whose text does not fit (a deliberately long German-like label)."""
    from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

    page = QWidget()
    qtbot.addWidget(page)
    label = QLabel("Ausgesprochen lange Beschriftung, die nicht passt", page)
    label.setObjectName("long_label")
    label.setFixedWidth(60)
    QVBoxLayout(page).addWidget(label)
    page.show()
    assert _gallery().cut_texts(page) == [("long_label", label.text())]


def test_a_small_button_and_a_control_off_the_tab_chain_are_found(qtbot):
    """ARC-19: hit targets and the focus chain are measured too."""
    from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QToolButton, QWidget

    page = QWidget()
    qtbot.addWidget(page)
    tiny = QToolButton(page)
    tiny.setObjectName("tiny")
    tiny.setToolTip("Tiny")
    tiny.setFixedSize(12, 12)
    field = QLineEdit(page)
    QHBoxLayout(page).addWidget(tiny)
    page.layout().addWidget(field)
    page.show()
    gallery = _gallery()
    assert gallery.small_targets(page) == [("tiny", "small target")]
    assert gallery.unreachable(page) == []  # the field is on the chain


def test_a_chain_that_goes_back_up_is_found_and_put_right(qtbot):
    """ARC-19: Tab must follow the reading order; read_in_order puts a late-made toolbar first."""
    from PySide6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

    from astrowb.ui.kit.focus import read_in_order

    page = QWidget()
    qtbot.addWidget(page)
    head, lower, upper = QLineEdit(page), QLineEdit(page), QLineEdit(page)  # lower is made first, drawn last
    upper.setObjectName("upper")
    lay = QVBoxLayout(page)
    lay.addWidget(head)
    lay.addWidget(upper)
    lay.addWidget(lower)
    page.show()
    gallery = _gallery()
    assert gallery.out_of_order(page) == [("upper", "Tab goes back up")]
    read_in_order(upper, lower)
    assert gallery.out_of_order(page) == []


def test_overlap_main_share_untranslated_and_contact_sheet(qtbot, tmp_path):
    """UI-15: labels laid over each other, a main view under 55 %, a finished translation not shown and the contact
    sheet are found / made."""
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

    gallery = _gallery()
    page = QWidget()
    qtbot.addWidget(page)
    QVBoxLayout(page)
    a, b = QLabel("A", page), QLabel("B", page)
    a.setObjectName("a")
    a.setGeometry(0, 0, 40, 20)
    b.setGeometry(10, 5, 40, 20)
    page.show()
    assert gallery.overlapping(page) == [("a", "overlaps QLabel")]
    win = QMainWindow()
    qtbot.addWidget(win)
    win.setCentralWidget(QWidget())
    win.resize(1000, 600)
    win.centralWidget().setFixedWidth(500)
    win.show()
    assert gallery.small_main_view(win) == [("main view", "50% of the window")]
    assert gallery._translations("tr").get("Images") == "Görüntüler"
    button = QPushButton("Images", page)
    button.show()
    assert ("QPushButton", "Images") in gallery.untranslated(page, "tr")
    shot = QImage(100, 60, QImage.Format_RGB32)
    gallery.contact_sheet([shot, shot], tmp_path / "s.jpg")
    assert QImage(str(tmp_path / "s.jpg")).size().toTuple() == (100, 30)
