"""UI-16.1 / PHO-W: the Images stage's summary, Multi-plot as a results tab, the target by name in the Field stage."""

import json

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from test_ui import window  # noqa: F401 — the main window fixture


def _frames(tmp_path, n=12, calibrated=True):
    rng = np.random.default_rng(3)
    y, x = np.mgrid[:60, :80]
    paths = []
    for i in range(n):
        img = rng.normal(100, 3, (60, 80))
        for sx, sy, f in ((30, 20, 20000.0), (55, 40, 15000.0), (15, 45, 12000.0)):
            img += f / (2 * np.pi * 1.5**2) * np.exp(-((x - sx) ** 2 + (y - sy) ** 2) / (2 * 1.5**2))
        cards = {"DATE-OBS": f"2026-10-01T20:{i * 5:02d}:00", "EXPTIME": 30.0, "FILTER": "V"}
        if calibrated:
            cards |= {"CALB": "master_bias.fits", "CALF": "master_flat_V.fits", "CALD": "none"}
        p = tmp_path / f"f{i:02d}.fits"
        fits.PrimaryHDU(img.astype(np.float32), fits.Header(cards)).writeto(p)
        paths.append(p)
    return paths


def _dir(root, name):
    (root / name).mkdir()
    return root / name


def _open(window):  # noqa: F811
    window.show_workspace("photometry")
    return window.area_windows["photometry"], window.photometry_page


def test_images_stage_summary(window, tmp_path):  # noqa: F811
    win, page = _open(window)
    label = win.stage_panels["images"].findChild(type(page.result), "images_summary")
    page.set_images(_frames(_dir(tmp_path, "a")))
    text = label.text()
    assert "12 frames over 0.9 h" in text and "Filters: V" in text
    assert "Calibrated: yes (bias, flat)" in text and "not checked yet" in text
    page.show_quality(
        [{"file": p, "good": i != 2, "why": [] if i != 2 else ["cloudy"], "fwhm": 3.0, "stars": 3, "background": 100.0}
         for i, p in enumerate(page.images)]
    )  # fmt: skip
    assert "Bad frames: 1" in label.text() and "f02.fits" in label.text()
    page.set_images(_frames(_dir(tmp_path, "b"), calibrated=False))
    assert "the headers do not say" in label.text()


def test_multi_plot_is_a_results_tab(window, qtbot, tmp_path):  # noqa: F811
    win, page = _open(window)
    tabs = page.res_tabs
    names = [tabs.tabText(i) for i in range(tabs.count())]
    assert "Multi-plot" in names and not win.stage_panels["lightcurve"].isAncestorOf(page.multi_box)
    tab = names.index("Multi-plot")
    tabs.setCurrentIndex(tab)
    assert tabs.currentIndex() == 0 and "Measure" in page.result.text()  # nothing measured: stays on the first tab
    page.set_images(_frames(tmp_path))
    for sx, sy in ((30, 20), (55, 40), (15, 45)):
        page._clicked(sx, sy)
    page.measure_button.click()
    qtbot.waitUntil(lambda: page.light_curve is not None, timeout=60000)
    tabs.setCurrentIndex(tab)  # the tab chooses the multi-plot view of the same plot
    assert page.show_what.currentData() == "multi" and not page.multi_box.isHidden()
    page.show_what.setCurrentIndex(page.show_what.findData("rel"))  # another view: the tab gives way
    assert tabs.currentIndex() == 0


def test_target_by_name_in_the_field_stage(window, monkeypatch, tmp_path):  # noqa: F811
    import astrowb.settings

    monkeypatch.setattr(astrowb.settings, "config_dir", lambda: tmp_path)
    (tmp_path / "targets.json").write_text(  # a name seen before: resolves offline
        json.dumps({"ny vir": {"name": "NY Vir", "ra": 31.0, "dec": 46.0, "vmag": None, "source": "SIMBAD"},
                    "far": {"name": "Far", "ra": 200.0, "dec": 10.0, "vmag": None, "source": "SIMBAD"}})
    )  # fmt: skip
    win, page = _open(window)
    page.set_images(_frames(tmp_path))
    page.target_name.setText("NY Vir")
    page.name_button.click()
    assert "Identify the field first" in page.name_answer.text() and page.target is None
    w = WCS(naxis=2)
    w.wcs.ctype, w.wcs.crval, w.wcs.crpix, w.wcs.cdelt = ["RA---TAN", "DEC--TAN"], [31.0, 46.0], [31, 21], [-3e-4, 3e-4]
    page.field = {"header": w.to_header().tostring(), "stars": {"x": [], "y": [], "gmag": []}, "variables": []}
    page.name_button.click()
    window.engine.wait_idle() if hasattr(window.engine, "wait_idle") else None
    from PySide6.QtTest import QTest

    for _ in range(100):
        if page.target is not None:
            break
        QTest.qWait(100)
    assert page.target is not None and np.allclose(page.target, (30, 20), atol=0.5)
    assert "NY Vir" in page.name_answer.text()
    page.target = None
    page.target_name.setText("Far")  # resolved, but off the frame: said, no target
    page.name_button.click()
    for _ in range(300):  # a loaded CI runner took over 10 s
        if "not on this field" in page.name_answer.text():
            break
        QTest.qWait(100)
    assert "not on this field" in page.name_answer.text() and page.target is None
    from astrowb.ui.photometry_name import fail

    fail(page, "cannot reach SIMBAD and 'X' is not in the local cache (URLError)")  # offline: a sentence, no crash
    assert "SIMBAD" in page.name_answer.text()
