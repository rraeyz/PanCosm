"""ARC-7: large frames show a preview at once and their full resolution from a background thread; the threaded
display conversion gives the same picture as the single block."""

import numpy as np

from astrowb import display


def test_threaded_conversion_equals_one_block(monkeypatch):
    data = np.random.default_rng(2).normal(100, 10, (2100, 2100)).astype(np.float32)
    data[7, 9] = np.nan
    threaded = display.to_display(data, limits=(80, 120))
    monkeypatch.setattr(display, "_cores", lambda: 1)
    assert np.array_equal(threaded, display.to_display(data, limits=(80, 120)))


def test_large_frame_preview_then_full_resolution(qapp):
    from astrowb.ui.viewer import PREVIEW_ABOVE, ImageViewer

    side = int(np.sqrt(PREVIEW_ABOVE)) + 100
    data = np.zeros((side, side), np.float32)
    v = ImageViewer()
    v.resize(600, 400)
    v.set_image(data)
    v.set_levels((0, 1))
    assert v._item.scale() > 1  # the preview, before the thread is done
    step = int(v._item.scale())
    top_row = (side - 1) // step * step  # the highest data row the preview sampled, drawn at the top
    corner = v._item.mapToScene(0.5, 0.5)  # centre of the preview's top-left pixel
    assert corner.x() == 0.5 and corner.y() == side - 1 - top_row + 0.5
    v.wait_rendered()
    assert v._item.scale() == 1 and v._item.pixmap().width() == side
    assert v.sceneRect().width() == side
    v.close()
