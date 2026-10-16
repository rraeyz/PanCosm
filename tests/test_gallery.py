"""UI-15: every window, in every interface language and both themes, at 1366 × 768: no label or button cuts its
text (tools/ui_gallery.py; its screenshots are for looking at, this test for the measurements)."""

import importlib.util
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

    found = _gallery().run(tuple(LANGUAGES), ("dark", "light"), settings_dir=tmp_path)
    assert found and all(key.count("-") >= 2 for key in found)
    cut = {k: v for k, v in found.items() if v}
    assert not cut, cut


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
