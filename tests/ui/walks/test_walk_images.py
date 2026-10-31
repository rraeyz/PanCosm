"""VAL-8: the Images window as a user goes through it: open a frame from the File menu, bin it from the Process
menu, take it back with Undo, save it."""

import pytest
from astropy.io import fits


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_open_bin_undo_and_save_an_image(walk, fits_file, tmp_path, lang):
    h = walk(lang)
    h.area("image")
    viewer = h.main.viewer
    h.answer(fits_file)
    h.menu("&Open…")
    h.wait(lambda: viewer.data is not None)
    assert viewer.data.shape == (64, 80)
    h.menu("Bin 2×2")
    h.wait(lambda: viewer.data.shape == (32, 40))
    h.menu("&Undo")
    h.wait(lambda: viewer.data.shape == (64, 80))
    out = tmp_path / "saved.fits"
    h.answer(out)
    h.menu("&Save FITS as…")
    h.wait(lambda: out.exists())
    h.check()
    assert fits.getheader(out)["OBJECT"] == "TEST" and fits.getdata(out).shape == (64, 80)
