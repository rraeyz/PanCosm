"""VAL-8: the practice long-slit night as a user goes through it (the guided task longslit.toml): extract, three
arc lines clicked on the plot and their wavelengths typed, the wavelength fit."""

import numpy as np
import pytest

from astrowb import sampledata


@pytest.mark.parametrize("lang", ["en", "tr"])
def test_practice_long_slit_spectrum_to_its_wavelengths(walk, tmp_path, lang):
    science, arc = sampledata.longslit(tmp_path)
    h = walk(lang)
    h.area("spectroscopy")
    tab = h.page.reduce_tab
    h.type("reduce_tab.science.edit", str(science))
    h.type("reduce_tab.arc.edit", str(arc))
    h.click("reduce_tab.extract_button")
    h.wait(lambda: tab.result is not None and tab._arc_ax is not None)
    for pixel, wavelength in ((269, "4471.477"), (578, "5015.675"), (1062, "5875.618")):
        h.click_plot(tab.plot, tab._arc_ax, pixel)
        h.keys(wavelength)
    h.click("reduce_tab.solve_button")
    h.wait(lambda: bool(tab.result.get("solution")))
    h.check()
    assert tab.result["solution"]["n_lines"] >= 3
    wave, flux = np.asarray(tab.result["wave"]), np.asarray(tab.result["flux"])
    near = (wave > 4840) & (wave < 4885)
    w, depth = wave[near], np.median(flux[near]) - flux[near]
    core = np.abs(w - w[np.argmax(depth)]) < 8  # the line's core, a pixel is 1.8 Å
    centre = np.sum(w[core] * depth[core]) / np.sum(depth[core])
    assert centre == pytest.approx(4862.0, abs=0.6)  # Hβ (4861.3 Å) moved by 45 km/s
