"""UI-16.13: the Layers list of the Remote sensing window: visibility, opacity and order of the drawn layers."""

import sys
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtGui import QImage

from astrowb.settings import Settings

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_remotesensing import scene  # noqa: E402


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path / "cfg"))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def picture(page):
    img = page.viewer._item.pixmap().toImage().convertToFormat(QImage.Format_RGB888)
    return (
        np.frombuffer(img.constBits(), np.uint8).reshape(img.height(), img.bytesPerLine())[:, : 3 * img.width()].copy()
    )


def opened(window, tmp_path):
    window.open_area("remotesensing")
    page = window.rs_page
    page.open(str(scene(tmp_path)[0]))
    return page


def test_layers_list_has_a_row_per_band_and_shows_the_chosen_one(window, tmp_path):
    page = opened(window, tmp_path)
    assert list(page.layers.rows) == page.raster.names
    assert [n for n, _ in page.layers.state()] == [page.raster.names[0]]


def test_hiding_a_layer_changes_the_picture_and_opacity_zero_equals_hidden(window, tmp_path):
    from astrowb.ui.rs_layers import draw

    page = opened(window, tmp_path)
    a, b = page.raster.names[:2]
    page.layers.rows[b][0].setChecked(True)
    both = picture(page)
    page.layers.rows[b][0].setChecked(False)
    hidden = picture(page)
    assert not np.array_equal(both, hidden)
    page.layers.rows[b][0].setChecked(True)
    page.layers.rows[b][1].setValue(0)
    assert np.array_equal(picture(page), hidden)
    page.layers.rows[b][1].setValue(100)
    page.layers.rows[a][0].setChecked(False)
    page.layers.rows[b][0].setChecked(False)
    draw(page)
    assert picture(page).max() == 0  # nothing visible: a black map


def test_the_layer_order_decides_what_is_on_top():
    from astrowb.ui.rs_layers import compose

    dark, light = np.zeros((2, 2), np.uint8), np.full((2, 2), 200, np.uint8)
    assert compose([(dark, 1.0), (light, 1.0)]).max() == 200
    assert compose([(light, 1.0), (dark, 1.0)]).max() == 0
    assert compose([(dark, 1.0), (light, 0.5)])[0, 0, 0] == 100
