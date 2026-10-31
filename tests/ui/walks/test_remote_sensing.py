"""VAL-8: the Remote sensing window as a user goes through it: a scene opened from the File menu, NDVI chosen,
Compute, then a k-means classification."""

import pytest
from test_remotesensing import scene


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_ndvi_and_classes_of_a_scene(walk, tmp_path, lang):
    path, _water, _veg = scene(tmp_path)
    h = walk(lang)
    h.area("remotesensing")
    page = h.page
    h.answer(path)
    h.menu("&Open…")
    h.wait(lambda: getattr(page, "raster", None) is not None)
    h.choose("index", page.index.findText("NDVI"))
    assert page.expression.text() == "(B4 - B3) / (B4 + B3)"
    h.click("compute_button")
    h.wait(lambda: "scene_ndvi" in page.products)
    before = set(page.products)
    h.click("classify_button")
    h.wait(lambda: set(page.products) - before)
    h.check()
    assert (tmp_path / "scene_ndvi.tif").exists()
