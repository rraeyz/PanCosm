"""IFU cubes: wavelength axis, images, line maps, spaxel spectra on a synthetic cube."""

import mmap

import numpy as np
import pytest
from astropy.io import fits

from astrowb.spectroscopy import cube


def make_cube(tmp_path, unit="nm", log=False):
    nw, ny, nx = 400, 25, 30
    wave_a = 6400 + 0.8 * np.arange(nw)  # Angstrom
    yy, xx = np.mgrid[:ny, :nx]
    galaxy = np.exp(-((xx - 15) ** 2 + (yy - 12) ** 2) / (2 * 4.0**2))
    halpha_spot = np.exp(-((xx - 20) ** 2 + (yy - 8) ** 2) / (2 * 1.5**2))
    cont = (1 + 0.0005 * (wave_a - 6400))[:, None, None] * galaxy[None]
    line = 5 * np.exp(-0.5 * ((wave_a - 6563) / 1.5) ** 2)[:, None, None] * halpha_spot[None]
    data = (100 * (cont + line)).astype(np.float32)
    h = fits.Header()
    if log:
        h["CTYPE3"] = "WAVE-LOG"
    h["CRVAL3"], h["CRPIX3"] = 6400 / (10 if unit == "nm" else 1), 1
    h["CDELT3"] = 0.8 / (10 if unit == "nm" else 1)
    h["CUNIT3"] = unit
    path = tmp_path / "cube.fits"
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(data, h)]).writeto(path)
    return path, wave_a, galaxy, halpha_spot


def test_cube_axis_images_line_map_spectrum(tmp_path):
    path, wave_a, galaxy, spot = make_cube(tmp_path)
    data, wave, _ = cube.read_cube(path)
    assert np.allclose(wave, wave_a) and data.shape == (400, 25, 30)
    base = data
    while getattr(base, "base", None) is not None:
        base = base.base
    assert isinstance(base, mmap.mmap)  # mapped from the file, not read into memory
    img = cube.image(data, wave, 6450, 6500)
    assert np.unravel_index(np.argmax(img), img.shape) == (12, 15)  # continuum peak at the galaxy centre
    lm = cube.line_map(data, wave, 6563, 12)
    assert np.unravel_index(np.argmax(lm), lm.shape) == (8, 20)  # the line-emitting spot, not the nucleus
    expected = 100 * 5 * 1.5 * np.sqrt(2 * np.pi)  # Gaussian line flux at the spot centre
    assert lm[8, 20] == pytest.approx(expected, rel=0.02)
    assert abs(lm[12, 15] - 100 * 5 * 1.5 * np.sqrt(2 * np.pi) * spot[12, 15]) < 0.02 * expected  # continuum removed
    spec = cube.spaxel_spectrum(data, 20, 8, radius=0.5)
    assert wave[np.argmax(spec)] == pytest.approx(6563, abs=0.8)


def test_units_and_errors(tmp_path):
    path, wave_a, _, _ = make_cube(tmp_path, unit="Angstrom")
    assert np.allclose(cube.read_cube(path)[1], wave_a)
    fits.PrimaryHDU(np.zeros((5, 5), np.float32)).writeto(tmp_path / "flat.fits")
    with pytest.raises(ValueError):
        cube.read_cube(tmp_path / "flat.fits")


def test_cube_tab(tmp_path, qtbot):
    from astrowb.spectroscopy import spectrum_io
    from astrowb.ui.spectro_page import SpectroscopyPage

    path, _, _, _ = make_cube(tmp_path)
    page = SpectroscopyPage()
    qtbot.addWidget(page)
    tab = page.cube_tab
    tab.open(str(path))
    assert "30 × 25" in tab.info.text()
    tab.mode.setCurrentIndex(1)
    tab.centre.setValue(6563)
    tab.width.setValue(12)
    tab.show_image()
    assert np.unravel_index(np.argmax(tab.viewer.data), tab.viewer.data.shape) == (8, 20)
    tab._clicked(20.0, 8.0)
    out = tab.save_spectrum(tmp_path / "spaxel.fits")
    w, f, _, h = spectrum_io.read(out)
    assert w[np.argmax(f)] == pytest.approx(6563, abs=0.8) and h["SPAXELX"] == 20
    assert page.velocity_tab.files.count() == 1


def test_scaled_integer_cube_is_read(tmp_path):
    """16-bit cubes with BZERO cannot be memory-mapped: read whole instead of an error."""
    import numpy as np
    from astropy.io import fits

    from astrowb.spectroscopy.cube import read_cube

    h = fits.Header({"CRVAL3": 5000.0, "CDELT3": 1.0, "CRPIX3": 1.0, "CUNIT3": "Angstrom"})
    fits.PrimaryHDU((np.arange(5 * 6 * 7) % 60000).astype(np.uint16).reshape(5, 6, 7), h).writeto(tmp_path / "c.fits")
    data, wave, _ = read_cube(tmp_path / "c.fits")
    assert data.shape == (5, 6, 7) and wave[0] == 5000.0 and data.max() > 200
