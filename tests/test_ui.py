import time

import numpy as np
import pytest
from astropy.io import fits
from PySide6.QtCore import Qt

from astrowb.display import INTERVALS, STRETCHES, to_display
from astrowb.settings import Settings


@pytest.mark.parametrize("interval", INTERVALS)
@pytest.mark.parametrize("stretch", STRETCHES)
def test_to_display_range(interval, stretch):
    data = np.linspace(-5, 1e4, 2000, dtype=np.float32).reshape(40, 50)
    data[0, 0] = np.nan
    out = to_display(data, interval, stretch)
    assert out.dtype == np.uint8 and out.shape == data.shape
    assert out[0, 0] == 0 and out.max() == 255


def test_to_display_constant_and_all_nan():
    assert to_display(np.full((4, 4), 7.0)).max() == 0
    assert to_display(np.full((4, 4), np.nan)).max() == 0


@pytest.fixture
def window(qtbot, tmp_path):
    from astrowb.ui.main_window import MainWindow

    win = MainWindow(Settings(tmp_path))
    qtbot.addWidget(win)
    yield win
    win.engine.shutdown()


def test_open_and_save(window, fits_file, tmp_path):
    window.open_project(tmp_path / "p.astroproj")
    assert window.open_fits(fits_file)
    assert window.header_table.rowCount() > 0
    assert window.viewer.data.shape == (64, 80)
    window.save_as(tmp_path / "copy.fits").result(60)
    assert fits.getheader(tmp_path / "copy.fits")["OBJECT"] == "TEST"
    assert window.files_list.count() == 1
    assert "frame.fits" in window.windowTitle()


def test_open_bad_file_keeps_window_usable(window, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    bad = tmp_path / "bad.fits"
    bad.write_text("not fits")
    assert not window.open_fits(bad)
    assert window.viewer.data is None


def test_pixel_readout_uses_fits_convention(window, fits_file):
    window.open_fits(fits_file)
    window._show_pixel(41, 31, 6000.0)
    assert "x=41" in window.pixel_label.text()


@pytest.mark.parametrize("lang,file_menu", [("tr", "&Dosya"), ("de", "&Datei"), ("es", "&Archivo")])
def test_translation_complete_and_loads(qapp, lang, file_menu):
    import subprocess
    import sys
    from pathlib import Path

    from PySide6.QtCore import QCoreApplication

    from astrowb.ui import i18n

    ts = (i18n.I18N_DIR / f"app_{lang}.ts").read_text(encoding="utf-8")
    assert 'type="unfinished"' not in ts
    if not (i18n.I18N_DIR / f"app_{lang}.qm").exists():
        subprocess.run([sys.executable, str(Path(__file__).parents[1] / "tools" / "i18n.py")], check=True)
    translators = i18n.install(qapp, lang)
    try:
        assert QCoreApplication.translate("MainWindow", "&File") == file_menu
    finally:
        for t in translators:
            qapp.removeTranslator(t)


def test_sidebar_has_every_stage_and_start_buttons_navigate(window, qtbot):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QPushButton

    assert list(window.workspaces)[:2] == ["start", "plan"] and "spectroscopy" in window.workspaces
    assert window.current_workspace() == "start"
    qtbot.mouseClick(window.start_page.findChild(QPushButton, "start_calibrate"), Qt.LeftButton)
    assert window.current_workspace() == "calibrate"


def test_opening_fits_switches_to_images_and_project_history(window, fits_file, tmp_path):
    window.open_project(tmp_path / "p.astroproj")
    window.open_fits(fits_file)
    assert window.current_workspace() == "image"
    window.save_as(tmp_path / "c.fits").result(60)
    time.sleep(0.2)  # the run is recorded on the task monitor thread
    window._refresh_files()
    assert window.project_page.runs_table.rowCount() == 1
    assert window.project_page.runs_table.item(0, 0).text() == "fits.save_as"


def test_compute_setting_saved(window):
    window.set_compute("cpu")
    from astrowb import compute

    assert window.settings.get("compute.device") == "cpu" and compute.mode() == "cpu"
    compute.set_mode("auto")


def test_calibrate_page_scan_and_run(window, qtbot, tmp_path):
    NY, NX = 30, 40
    rng = np.random.default_rng(0)
    raw = tmp_path / "raw"
    raw.mkdir()
    for i in range(3):
        fits.PrimaryHDU(rng.normal(500, 5, (NY, NX)).astype(np.float32), fits.Header({"IMAGETYP": "BIAS"})).writeto(
            raw / f"b{i}.fits"
        )
        fits.PrimaryHDU(
            rng.normal(1500, 5, (NY, NX)).astype(np.float32), fits.Header({"IMAGETYP": "LIGHT", "EXPTIME": 10.0})
        ).writeto(raw / f"l{i}.fits")
    window.open_project(tmp_path / "p.astroproj")
    page = window.calibrate_page
    page.folder.setText(str(raw))
    window.scan_raw(str(raw)).result(60)
    qtbot.waitUntil(lambda: page.table.rowCount() == 6, timeout=5000)
    assert page.run_button.isEnabled() and "dark" in page.warnings.toPlainText()  # no darks/flats: reported
    assert page.output.text().endswith("calibrated")
    page.linearity.setText("0 one")
    page.run_button.click()
    assert "Linearity" in page.result.text()  # not understood: nothing runs
    page.linearity.setText("0, 1")  # identity: the result must not change
    page.run_button.click()
    qtbot.waitUntil(lambda: "3" in page.result.text(), timeout=60000)
    kinds = sorted(f["kind"] for f in window.engine.project.files())
    assert kinds == ["calibrated"] * 3 + ["master"]
    assert abs(np.median(fits.getdata(raw / "calibrated" / "l0.fits")) - 1000) < 5
    # step 4: the calibrated lights go to the Photometry page, which opens
    assert page.photometry_button.isEnabled()
    page.photometry_button.click()
    assert window.current_workspace() == "photometry" and len(window.photometry_page.images) == 3
    # a frame's type can be changed on the page: a light taken for a bias is not calibrated as a light
    page._edit_kind(3, 1)
    box = page.table.cellWidget(3, 1)
    box.activated.emit(box.findData("unknown"))
    assert page.frames[3]["kind"] == "unknown" and "unknown" in page.table.item(3, 1).text()
    assert "ignored" in page.warnings.toPlainText()


def test_photometry_page_click_measure_minimum(window, qtbot, tmp_path):
    """Synthetic transit: three stars drift across frames, the target dims by 3 % mid-series."""
    rng = np.random.default_rng(2)
    y, x = np.mgrid[:60, :80]
    stars = [(30, 20, 20000.0), (55, 40, 15000.0), (15, 45, 12000.0)]  # x, y, flux
    paths = []
    for i in range(30):
        dx, dy = 0.3 * i, -0.2 * i
        img = rng.normal(100, 3, (60, 80))
        for k, (sx, sy, f) in enumerate(stars):
            f = f * (0.97 if (k == 0 and 10 <= i < 20) else 1.0)
            img += f / (2 * np.pi * 1.5**2) * np.exp(-((x - sx - dx) ** 2 + (y - sy - dy) ** 2) / (2 * 1.5**2))
        h = fits.Header({"DATE-OBS": f"2026-10-01T20:{i:02d}:00", "EXPTIME": 30.0, "GAIN": 2.0})
        p = tmp_path / f"f{i:02d}.fits"
        fits.PrimaryHDU(img.astype(np.float32), h).writeto(p)
        paths.append(p)
    page = window.photometry_page
    page.set_images(paths)
    for sx, sy, _ in stars:
        page._clicked(sx, sy)
    assert page.target == (30, 20) and len(page.comps) == 2 and page.measure_button.isEnabled()
    page.coord.setText("02:04:10 +46:41:16")
    page.measure_button.click()
    qtbot.waitUntil(lambda: page.light_curve is not None, timeout=60000)
    rel = np.array(page.light_curve["rel_flux"])
    assert abs(rel[12] / rel[2] - 0.97) < 0.01 and page.light_curve["time_scale"] == "BJD_TDB"
    out = tmp_path / "lc.csv"
    from astrowb.ui.workspaces import export_csv

    export_csv(page.light_curve, out)
    assert out.read_text().splitlines()[0].startswith("BJD_TDB,rel_flux")


def test_oc_page_fit_and_errors(window):
    page = window.oc_page
    t0, p = 2455867.402743, 2.1500082
    rng = np.random.default_rng(4)
    lines = [f"{t0 + e * p + rng.normal(0, 0.0003):.6f} 0.0003 I" for e in (-500, -120, 0, 300, 700, 1050)]
    lines.append(f"{t0 + 400.5 * p:.6f} 0.0004 II")
    page.text.setPlainText("\n".join(lines))
    page.t0.setText(str(t0))
    page.period.setText(str(p))
    f = page.run_fit()
    assert f is not None and abs(f.period - p) < 3 * f.period_err
    assert "P = 2.150008" in page.result.text() and len(page.plot.figure.axes) == 2
    page.period.setText("abc")
    assert page.run_fit() is None and page.result.text().startswith("Give the reference T0")


def test_stack_from_calibrate_page(window, qtbot, tmp_path):
    rng = np.random.default_rng(0)
    paths = []
    for i in range(4):
        img = rng.normal(100, 5, (40, 50))
        img[20 + i // 2, 25 + i] += 3000
        p = tmp_path / f"c{i}.fits"
        fits.PrimaryHDU(img.astype(np.float32)).writeto(p)
        paths.append(str(p))
    page = window.calibrate_page
    page.output.setText(str(tmp_path))
    page.show_result({"calibrated": paths, "masters": []})
    assert page.stack_button.isEnabled()
    page.stack_button.click()
    qtbot.waitUntil(lambda: (tmp_path / "stack.fits").exists() and window.current_workspace() == "image", timeout=60000)
    assert fits.getheader(tmp_path / "stack.fits")["NCOMBINE"] == 4


def test_aavso_dialog_values(qtbot):
    from astrowb.ui.workspaces import AavsoDialog

    d = AavsoDialog(2)
    qtbot.addWidget(d)
    d.star.setText("HAT-P-32")
    d.obscode.setText("xyz")
    d.mags.setText("11.2; 11.85")
    d.notes.setText("clear, calm")
    v = d.values()
    assert v["comp_mags"] == [11.2, 11.85] and v["obscode"] == "XYZ" and v["notes"] == "clear; calm"


def test_period_search_tab(window, qtbot):
    page = window.period_page
    t = np.linspace(0, 10, 400)
    page.set_light_curve(t, 1 + 0.05 * np.sin(2 * np.pi * t / 0.731), "test")
    page.p_min.setValue(0.2)
    page.p_max.setValue(3.0)
    page.search_button.click()
    qtbot.waitUntil(lambda: page.best is not None, timeout=60000)
    assert abs(page.best - 0.731) < 0.002
    assert window.lightcurve_page.count() == 4
    page.phase_bins.setValue(20)  # binned mean curve drawn over the folded points
    assert len(window.period_page.plot.figure.axes[1].containers) == 1

    rng = np.random.default_rng(3)  # an eclipsing binary: with the period known, outliers are judged in phase
    t = np.sort(np.concatenate([n * 1.7 + rng.uniform(0, 0.3, 120) for n in range(25)]))
    ph = (t / 0.8137 + 0.5) % 1 - 0.5
    y = 1 - 0.4 * np.exp(-0.5 * (ph / 0.025) ** 2) + rng.normal(0, 0.005, t.size)
    y[17] = 1.3
    page.set_light_curve(t, y, "binary")
    page.best, page.periodogram = 0.8137, {"periods": [0.8137], "power": [1.0]}
    page._clip()
    assert 1.3 not in page.flux and len(page.time) >= t.size - 10  # the eclipses stay


def test_oc_asks_for_the_ephemeris(window):
    oc = window.oc_page
    oc.text.setPlainText("2460500.31 0.001 I\n2460510.08 0.001 I\n2460520.66 0.001 I")
    oc.fit_button.click()
    assert oc.result.text() == "Give the reference T0 and the period in days." and oc.fit_result is None
    oc.t0.setText("2460500.31")
    oc.period.setText("0.8137")
    oc.fit_button.click()
    assert oc.fit_result is not None


def test_frequency_analysis_and_light_curve_editing(window, qtbot):
    page, freq = window.period_page, window.lightcurve_page.frequency_page
    rng = np.random.default_rng(2)
    t = np.concatenate([n + np.linspace(0, 0.3, 120) for n in range(6)])
    y = 1 + 0.05 * np.sin(2 * np.pi * 5.3 * t) + 0.02 * np.sin(2 * np.pi * 8.1 * t) + rng.normal(0, 0.002, t.size)
    y[10] = 3.0
    page.set_light_curve(t, y, "test")
    page.clip_sigma.setValue(5)
    page._clip()
    assert len(page.time) == t.size - 1
    page._bin()  # 5-minute bins
    assert len(page.time) < t.size - 1
    page._convert()
    assert page.magnitudes and max(page.flux) < 0.1
    page._undo()
    assert len(page.time) == t.size and not page.magnitudes
    page._clip()
    freq.f_max.setValue(15)
    freq.clean.setChecked(True)
    freq.button.click()
    qtbot.waitUntil(lambda: freq.result is not None, timeout=60000)
    found = sorted(float(freq.table.item(r, 0).text()) for r in range(freq.table.rowCount()))
    assert len(found) == 2 and abs(found[0] - 5.3) < 0.01 and abs(found[1] - 8.1) < 0.01
    assert len(freq.result["clean_spectrum"]) == len(freq.result["grid"])
    assert freq.maxima.rowCount() >= 4
    freq.to_oc.click()
    assert window.oc_page.text.toPlainText().count("maximum") == freq.maxima.rowCount()


def test_suggest_comparisons():
    from astrowb.photometry.aperture import suggest_comparisons

    rng = np.random.default_rng(1)
    y, x = np.mgrid[:120, :160]
    img = rng.normal(100, 3, (120, 160))
    stars = {
        "target": (80, 60, 5000),
        "good": (40, 30, 6000),
        "close_pair": (120, 90, 5000),
        "neighbour": (126, 92, 5000),
        "faint": (40, 90, 800),
        "saturated": (130, 30, 90000),
        "edge": (3, 60, 5000),
    }
    for sx, sy, f in stars.values():
        img += f / (2 * np.pi * 1.5**2) * np.exp(-((x - sx) ** 2 + (y - sy) ** 2) / (2 * 1.5**2))
    img = np.minimum(img, 4000)  # saturation
    picks = suggest_comparisons(img, (80, 60), r_out=16)
    assert len(picks) == 1 and abs(picks[0][0] - 40) < 1 and abs(picks[0][1] - 30) < 1
    assert suggest_comparisons(img, (80, 60), r_out=16, offsets=[(0, 0), (-30, 0)]) == []  # drifts off the edge


def test_plan_page_resolve_and_plan(window, qtbot):
    from PySide6.QtCore import QDate

    page = window.plan_page
    page.lat.setValue(36.82)
    page.lon.setValue(30.34)
    page.date.setDate(QDate(2026, 11, 15))
    page.target_input.setText("02:04:10.3 +46:41:16")  # coordinates: no network needed
    page._add()
    qtbot.waitUntil(lambda: page.table.rowCount() == 1, timeout=60000)
    page.table.item(0, 3).setText("2455867.402743")
    page.table.item(0, 4).setText("2.1500082")
    page.table.item(0, 5).setText("0.13")
    page.utc_offset.setValue(3.0)  # Turkey; Auto takes this computer's time zone
    page.plan_button.click()
    qtbot.waitUntil(lambda: page.result is not None, timeout=120000)
    assert page.result["dusk"] and len(page.result["targets"][0]["alt"]) > 200
    assert window.settings.get("site")["lat"] == 36.82 and window.settings.get("plan.utc_offset") == 3.0
    # the chart is in English (for papers) with the local time above the UTC axis
    ax = page.plot.figure.axes[0]
    labels = [a.get_xlabel() for a in [ax, *ax.child_axes]] + [ax.get_ylabel()]
    assert "UTC (hours)" in labels and "Local time (UTC+3, hours)" in labels and "Altitude (°)" in labels
    if page.events.rowCount():
        utc, local = page.events.item(0, 3).text()[11:16], page.events.item(0, 4).text()
        assert (int(local[:2]) - int(utc[:2])) % 24 == 3 and local[3:] == utc[3:]
    page.utc_offset.setValue(page.utc_offset.minimum())
    assert page.utc_offset.text() == "Auto" and -12 <= page.local_offset(2461360.0) <= 14
    page.table.item(0, 4).setText("x")
    page._plan()
    assert page.status.text().startswith("Row 1")


def test_echelle_tab_identifies_lines_with_order_numbers(window):
    from types import SimpleNamespace

    tab = window.spectro_page.echelle_tab
    arc = np.zeros((3, 200))
    arc[:, 50] = arc[:, 120] = 100
    tab.first_order.setValue(40)
    tab.direction.setCurrentIndex(1)  # numbers decrease upwards
    tab.show_result(
        {"n_orders": 3, "flux": arc.tolist(), "arc": arc.tolist(), "arc_peaks": [[50.0, 120.0]] * 3, "solution": None}
    )
    tab.order_view.setValue(2)
    tab._plot_clicked(SimpleNamespace(inaxes=tab._arc_ax, xdata=118.0))
    assert tab.guesses.item(0, 0).text() == "38" and tab.guesses.item(0, 1).text() == "120.00"
    tab.guesses.item(0, 2).setText("5000.5")
    assert tab._guesses() == [[38.0, 120.0, 5000.5]]
    tab._run(True)  # no science frame yet: refused with a message, nothing emitted
    assert tab.status.text()


def test_models_page_fits_a_light_curve(window, qtbot, tmp_path):
    from astrowb.models import fit

    truth = {
        "period": 1.7,
        "t0": 2459500.25,
        "r_sum": 0.3,
        "k": 0.6,
        "incl": 86.0,
        "j": 0.5,
        "ecosw": 0.0,
        "esinw": 0.0,
        "l3": 0.0,
    }
    rng = np.random.default_rng(3)
    t = np.sort(rng.uniform(2459500, 2459510, 800))
    f = fit.model(t, truth, (0.4, 0.2), (0.4, 0.2)) + rng.normal(0, 0.003, len(t))
    path = tmp_path / "lc.csv"
    path.write_text("BJD_TDB,rel_flux,rel_flux_err\n" + "\n".join(f"{a},{b},0.003" for a, b in zip(t, f, strict=True)))
    page = window.models_page
    assert window.workspaces["orbits"][1] is page
    page.file.edit.setText(str(path))
    for r, name in enumerate(("period", "t0")):
        page.table.item(r, 1).setText(str(truth[name]))
    page.table.item(4, 1).setText("84")  # inclination start
    page.fit_button.click()
    qtbot.waitUntil(lambda: page.result is not None, timeout=60000)
    assert abs(page.result["params"]["incl"] - 86) < 4 * page.result["errors"]["incl"]
    assert "i = " in page.status.text()
    page.set_orbit({"k2": 100.0, "m1_sin3i": 1.0})
    assert page.use_orbit.isEnabled()
    model = tmp_path / "phoebe_model.txt"
    model.write_text(
        "\n".join(f"{p} {v}" for p, v in zip(page.result["model_phase"], page.result["model_flux"], strict=True))
    )
    page.load_overlay(model)
    assert page.overlay is not None and np.all(np.isfinite(page.overlay[1]))  # a curve to draw, not NaN
    samples = np.random.default_rng(1).normal([86.0, 0.3], [0.2, 0.01], (500, 2)).tolist()
    mcmc = {"params": {"incl": (86.0, 0.2, 0.2), "r_sum": (0.3, 0.01, 0.01)}, "names": ["incl", "r_sum"]}
    mcmc["params"]["t0"] = (2459500.251234, 3e-5, 3e-5)
    page.show_fit(page.result | {"mcmc": mcmc | {"samples": samples, "acceptance": 0.4}})
    assert "MCMC (acceptance 0.40)" in page.status.text() and page.posterior_button.isVisibleTo(page)
    assert "t0 = 2459500.251234" in page.status.text()
    rows, caption = page.fit_table()  # MCMC values where sampled, the covariance elsewhere, fixed ones marked
    names = {r[0]: r for r in rows}
    assert names["incl"][1:3] == (86.0, 0.2) and names["t0"][1] == 2459500.251234 and "MCMC" in caption
    assert names["l3 (fixed)"][2] is None and "800 points" in caption and "r1" in names
    dlg = page.show_posterior()
    assert len(dlg.findChildren(type(page.plot))[0].figure.axes) == 4
    dlg.close()
    path.write_text("not a light curve\n")  # a failed fit says why on the page, not "Fitting…" for ever
    page.fit_button.click()
    qtbot.waitUntil(lambda: page.status.text() != "Fitting…", timeout=60000)
    assert "i = " not in page.status.text()


def test_spectroscopy_instrument_profiles(window):
    page = window.spectro_page
    page.echelle_tab.orientation.axis.setCurrentIndex(1)
    page.echelle_tab.orientation.reverse.setChecked(True)
    page.echelle_tab.fibre.setChecked(True)
    page.echelle_tab.first_order.setValue(88)
    page.reduce_tab.width.setValue(14)
    page.save_profile("coude test")
    assert page.profile.currentText() == "coude test"
    page.echelle_tab.restore({})
    page.reduce_tab.width.setValue(10)
    assert not page.echelle_tab.fibre.isChecked()
    page.apply_profile("coude test")
    assert page.echelle_tab.fibre.isChecked() and page.echelle_tab.first_order.value() == 88
    assert page.reduce_tab.width.value() == 14
    params = page.echelle_tab.orientation.params()
    assert params == {"orientation": "y", "reverse": True}
    assert "coude test" in window.settings.get("spectroscopy.profiles")


def test_photometry_live_mode(window, qtbot, tmp_path):
    import os

    from test_live import STARS, write_frames

    folder = tmp_path / "night"
    folder.mkdir()
    paths = write_frames(folder, 6)
    page = window.photometry_page
    assert page.start_live(str(folder)) is False  # no stars yet: the first frame is shown to click them
    assert page.images == [paths[0]]
    for sx, sy, _ in STARS:
        page._clicked(sx, sy)
    assert page.start_live(str(folder)) is True
    qtbot.waitUntil(lambda: page.light_curve is not None and len(page.light_curve["rel_flux"]) == 6, timeout=30000)
    # a new frame arrives during the night
    more = write_frames(tmp_path, 7)[-1]
    new = folder / "f06.fits"
    os.replace(more, new)
    os.utime(new, (1, 1))
    page.poll_live()
    qtbot.waitUntil(lambda: len(page.light_curve["rel_flux"]) == 7, timeout=30000)
    page.stop_live()


def test_remote_sensing_page(window, qtbot, tmp_path):
    from test_remotesensing import scene

    path, water, veg = scene(tmp_path)
    page = window.rs_page
    assert window.workspaces["remotesensing"][1] is page
    page.open(str(path))
    assert "EPSG:32635" in page.info.text() and page.roles["NIR"].currentText() == "B4"
    page.index.setCurrentIndex(page.index.findText("NDVI"))
    page._preset(page.index.findText("NDVI"))
    assert page.expression.text() == "(B4 - B3) / (B4 + B3)"
    page.compute_button.click()
    qtbot.waitUntil(lambda: "scene_ndvi" in page.products, timeout=60000)
    assert (tmp_path / "scene_ndvi.tif").exists() and page.show_combo.currentText() == "scene_ndvi"
    # the viewer shows north up: the top-left image pixel is at the top of the view
    page._hover(1, page.raster.shape[0], 0.0)  # viewer pixel (1, ny) in FITS convention = image (0, 0)
    assert "pixel 0, 0" in page.readout.text() and "X 500015.00" in page.readout.text()
    page._clicked(70.0, page.raster.shape[0] - 1 - 10.0)
    assert len(page.plot.figure.axes) == 1
    page.expression.setText("os.system('x')")
    page._compute()
    assert "not allowed" in page.status.text()


def test_image_process_menu(window, qtbot, fits_file):
    window.open_fits(fits_file)
    assert window.process_menu.isEnabled()
    window.process_image("bin", {"factor": 2})
    qtbot.waitUntil(lambda: window.current_path.name.endswith("_bin.fits"), timeout=60000)
    assert window.viewer.data.shape[0] > 0
    window.process_dialog(("flip", {"axis": "x"}))
    qtbot.waitUntil(lambda: "_bin_flip" in window.current_path.name, timeout=60000)
    window.process_dialog(("ddp", {}))
    qtbot.waitUntil(lambda: "_ddp" in window.current_path.name, timeout=60000)
    window.process_image("deconvolve", {"fwhm": 2.5, "iterations": 3})
    qtbot.waitUntil(lambda: "_deconvolve" in window.current_path.name, timeout=60000)


def test_automation_page_template_sequence_build_save_run(window, qtbot, fits_file, tmp_path):
    page = window.automation_page
    names = [page.list.item(i).text() for i in range(page.list.count())]
    page.list.setCurrentRow(next(i for i, n in enumerate(names) if n.startswith("Eclipsing binary night")))
    assert [e["step"] for e in page.auto["steps"]][-1] == "timeseries.minimum"
    assert page.input_names() == ["folder", "output_dir", "target_xy"]
    page.sequence_button.click()  # the observing part fills the Observe page
    assert window.current_workspace() == "observe"
    obs = window.observe_page
    assert obs.seq_start.text() == "dusk" and obs.seq_end.text() == "dawn"
    assert obs.exposures.rowCount() == 1 and obs.exposures.item(0, 1).text() == "V"
    assert obs.sequence_spec()["targets"][0]["exposures"][0]["exptime"] == 60

    page.new()  # build one from scratch: copy a FITS file twice
    page.add_step("fits.save_as")
    page.add_step("fits.save_as")
    t = page.settings_table
    rows = {t.item(r, 0).data(0x0100)[1]: r for r in range(t.rowCount())}  # Qt.UserRole
    t.item(rows["source"], 1).setText("destination")
    t.item(rows["destination"], 1).setText("{second}")
    t.item(rows["overwrite"], 1).setText("true")
    assert page.auto["steps"][1] == {
        "step": "fits.save_as",
        "inputs": {"source": "destination", "destination": "{second}"},
        "params": {"overwrite": True},
    }
    assert page.input_names() == ["source", "destination", "second"]
    page._run()
    assert page.status.text().startswith("Cannot run")  # nothing filled in yet
    for name, value in (("source", fits_file), ("destination", tmp_path / "a.fits"), ("second", tmp_path / "b.fits")):
        page.edits[name].setText(str(value))
    page.save_as("Copy twice")
    assert page.list.currentItem().text() == "Copy twice" and page.edits["second"].text().endswith("b.fits")
    page._run()
    qtbot.waitUntil(lambda: page.status.text() == "Finished.", timeout=60000)
    assert (tmp_path / "b.fits").exists() and "b.fits" in page.result.toPlainText()


def test_guide_categories_translations_and_search(window, qtbot):
    import re

    from astrowb.ui import guide_page
    from astrowb.ui.i18n import LANGUAGES

    en, tr = guide_page.load("en"), guide_page.load("tr")
    assert len(en) >= 12
    for lang in LANGUAGES:  # every interface language has its own complete guide, bundled (no online translation)
        assert sorted(p.name for p in (guide_page.GUIDE / lang).glob("*.md")) == [
            p.name for p in sorted((guide_page.GUIDE / "en").glob("*.md"))
        ]
        own = guide_page.load(lang)
        assert [len(t) for _, _, t in own] == [len(t) for _, _, t in en]  # translated topic by topic
        assert all(intro and topics for _, intro, topics in own)
        for _, _, topics in own:
            for _, text in topics:
                for image in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
                    assert image.startswith(f"images/{lang}/") and (guide_page.GUIDE / image).exists(), image
    assert tr[0][0] == "Başlarken" and guide_page.load("xx")[0][0] == en[0][0]  # no translation: English
    page = window.workspaces["guide"][1]
    window.show_workspace("guide")
    assert page.tree.topLevelItemCount() == len(en)
    assert "Getting started" in page.text.toPlainText()
    hits = page.filter("dither PHD2")
    assert 0 < hits < 10 and "dither" in page.text.toPlainText().lower()
    assert page.filter("no-such-word-anywhere") == 0
    page.filter("")
    assert not any(page.tree.topLevelItem(i).isHidden() for i in range(page.tree.topLevelItemCount()))


def test_automation_processes_the_night_when_the_sequence_ends(window, qtbot, fits_file):
    page = window.automation_page
    auto = {"name": "scan after the night", "steps": [{"step": "calibration.scan"}], "sequence": {"name": "t"}}
    page.set_automation(auto)
    assert page.after_night.isVisibleTo(page)
    page.after_night.setChecked(True)
    page.sequence_button.click()
    assert window.current_workspace() == "observe" and window.observe_page.seq_name.text() == "t"
    window.observe_page.sequence_finished.emit(str(fits_file.parent))
    assert page.edits["folder"].text() == str(fits_file.parent)
    qtbot.waitUntil(lambda: page.status.text() == "Finished.", timeout=60000)
    assert "frame.fits" in page.result.toPlainText()
    window.observe_page.sequence_finished.emit(str(fits_file.parent))  # not armed any more: nothing runs
    assert page.status.text() == "Finished."


def test_start_up_does_not_load_heavy_libraries(tmp_path):
    """Pages are built when first shown: opening the window must not import the science stack."""
    import subprocess
    import sys

    code = (
        "import sys; from PySide6.QtWidgets import QApplication; app = QApplication([]);"
        "from astrowb.settings import Settings; from astrowb.ui.main_window import MainWindow;"
        f"w = MainWindow(Settings(__import__('pathlib').Path({str(tmp_path)!r}))); w.show(); app.processEvents();"
        "heavy = [m for m in ('matplotlib', 'scipy.optimize', 'scipy.signal', 'astropy.coordinates')"
        " if m in sys.modules];"
        "w.engine.shutdown(); print(heavy)"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=120)
    assert out.stdout.strip().splitlines()[-1] == "[]", out.stdout + out.stderr


def test_update_check(window, qtbot):
    from astrowb import updates

    assert updates.version_tuple("v1.10.2") > updates.version_tuple("1.9.9")
    assert updates.check(lambda: {"version": "0.0.1", "url": "u"}, current="0.0.1") == (None, None)
    newer, err = updates.check(lambda: {"version": "2.0.0", "url": "https://x/r"}, current="0.0.1")
    assert newer["version"] == "2.0.0" and err is None

    def offline():
        raise OSError("no network")

    assert updates.check(offline) == (None, "no network")
    window.check_updates(fetch=lambda: {"version": "99.0", "url": "https://x/r"})
    qtbot.waitUntil(lambda: hasattr(window, "update_box") and window.update_box.isVisible(), timeout=10000)
    assert "99.0" in window.update_box.text() and "https://x/r" in window.update_box.text()
    window.update_box.close()


def test_night_schedule_goes_to_the_observe_page(window):
    from test_schedule import JD, TARGETS, night, target

    page = window.plan_page
    page.result, page._planned = night(target("A", JD[30]), target("B", JD[100])), TARGETS[:2]
    blocks = page.make_schedule()
    assert [b["name"] for b in blocks] == ["A", "B"] and page.schedule_table.rowCount() == 2
    page.send_button.click()
    obs = window.observe_page
    assert window.current_workspace() == "observe" and obs.plan_list.count() == 2
    spec = obs.sequence_spec()
    assert [t["name"] for t in spec["targets"]] == ["A", "B"]
    assert spec["targets"][0]["start"][10] == "T"  # ISO UTC, read by the observatory
    assert spec["targets"][1]["exposures"] == spec["targets"][0]["exposures"] and "end" in spec["targets"][1]
    obs.load_schedule([])
    assert len(obs.sequence_spec()["targets"]) == 1


def test_project_history_details_and_run_again(window, qtbot, fits_file, tmp_path):
    window.open_project(tmp_path / "p.astroproj")
    window.run_step(
        "fits.save_as", {"source": str(fits_file), "destination": str(tmp_path / "copy.fits")}, {"overwrite": True}
    )
    page = window.project_page
    qtbot.waitUntil(
        lambda: page.runs_table.rowCount() == 1 and page.runs_table.item(0, 1).text() == "done", timeout=60000
    )
    page.runs_table.selectRow(0)
    text = page.details.toPlainText()
    assert "fits.save_as — done" in text and "copy.fits" in text and "astropy" in text  # inputs, outputs, versions
    (tmp_path / "copy.fits").unlink()
    page.rerun_button.click()
    qtbot.waitUntil(
        lambda: page.runs_table.rowCount() == 2 and page.runs_table.item(1, 1).text() == "done", timeout=60000
    )
    assert (tmp_path / "copy.fits").exists() and window.engine.project.runs(full=False)[1]["params"] == {
        "overwrite": True
    }


def test_plan_page_target_with_ephemeris(window):
    page = window.plan_page
    page.add_target(
        {
            "name": "AI Dra",
            "ra": 250.68,
            "dec": 52.69,
            "t0": 2443300.444,
            "period": 1.1988146,
            "duration": 0.1439,
            "secondary": True,
            "source": "VSX",
        }
    )
    t = page.targets()[-1]
    assert t["t0"] == 2443300.444 and t["period"] == 1.1988146 and t["duration"] == 0.1439 and t["secondary"]


@pytest.mark.parametrize("lang", ["en", "tr", "de", "es"])
def test_window_fits_a_small_laptop_screen_in_every_language(qapp, qtbot, tmp_path, lang):
    """Long translations or crowded pages must scroll inside the page, never make the window bigger than
    a 1280 x 720 screen."""
    from astrowb.ui import i18n
    from astrowb.ui.main_window import MainWindow

    translators = i18n.install(qapp, lang)
    s = Settings(tmp_path)
    s.set("ui.language", lang)
    win = MainWindow(s)
    qtbot.addWidget(win)
    try:
        for key in win.workspaces:  # every page built
            win.show_workspace(key)
        hint = win.minimumSizeHint()
        assert hint.width() <= 1280 and hint.height() <= 720, (lang, hint)
    finally:
        win.engine.shutdown()
        for t in translators:
            qapp.removeTranslator(t)


def test_multi_extension_file_opens_the_chosen_image(window, tmp_path, monkeypatch):
    from astropy.io import fits

    path = tmp_path / "mef.fits"
    prim = fits.PrimaryHDU(header=fits.Header({"TELESCOP": "T1", "DATE-OBS": "2026-11-03T20:00:00"}))
    sci = fits.ImageHDU(np.ones((20, 30), np.float32), name="SCI")
    err = fits.ImageHDU(np.full((20, 30), 7.0, np.float32), name="ERR")
    fits.HDUList([prim, sci, err]).writeto(path)
    labels = []

    def choose(parent, title, text, items, *a):
        labels.extend(items)
        return items[1], True

    monkeypatch.setattr("PySide6.QtWidgets.QInputDialog.getItem", choose)
    assert window.open_fits(path, ask=True)
    assert labels == ["1: SCI (30 x 20)", "2: ERR (30 x 20)"]
    assert window.current_path.name == "mef_ERR_2.fits" and float(window.viewer.data.max()) == 7.0
    h = fits.getheader(window.current_path)
    assert h["TELESCOP"] == "T1" and "XTENSION" not in h  # the primary header's keywords travel with it
    assert fits.getdata(path, 2).max() == 7.0  # the original is untouched


def test_sidebar_groups_and_collapsible_options(window, qtbot):
    from PySide6.QtCore import Qt

    headings = [window.nav.item(i) for i in range(window.nav.count()) if not window.nav.item(i).data(Qt.UserRole)]
    assert len(headings) == 4 and all(h.flags() == Qt.NoItemFlags for h in headings)  # not selectable
    window.show_workspace("photometry")
    assert window.current_workspace() == "photometry"
    page = window.calibrate_page
    assert page.more_options.content.isHidden() and page.stack_options.content.isHidden()  # closed at first
    page.more_options.button.click()
    assert not page.more_options.content.isHidden() and page.split_colour.isChecked()


def test_image_panel_in_its_own_window_and_photometry_other_tools(window, fits_file):
    page = window.image_page
    window.show()
    window.open_fits(fits_file)
    assert page.floating and page.tabs.count() == 1  # results go to small tool windows; the header stays in its tab
    page.measure_star(41.5, 31.5)  # the "star" of the test frame: as clicking it with the Star tool
    info, graph = page.tool_windows["info"], page.tool_windows["graph"]
    assert info.isVisible() and graph.isVisible() and page.info.rowCount() > 5
    assert info.windowFlags() & Qt.Tool and info.width() < 600  # small, over the main window, as in MaxIm DL
    info.close()  # closing only hides it: the next measurement brings it back
    page.measure_line(5, 5, 60, 40)
    assert info.isVisible()
    page.float_button.setChecked(False)  # back to the tabs beside the image
    assert page.tabs.count() == 3 and not page.tool_windows and page.info.parent() is not None
    page.measure_star(41.5, 31.5)
    assert page.tabs.currentWidget() is page.info
    page.float_button.setChecked(True)
    phot = window.photometry_page
    assert not phot.other_tools.content.isVisible()  # live and polarimetry wait behind "Other tools"
    assert (
        phot.live_button.parent() is phot.other_tools.content and phot.pol_button.parent() is phot.other_tools.content
    )


def test_convert_many_images_from_the_file_menu(window, qtbot, fits_file, tmp_path):
    window.convert_dialog([str(fits_file)], str(tmp_path / "pictures"), "jpg")
    qtbot.waitUntil(lambda: (tmp_path / "pictures" / "frame.jpg").exists(), timeout=60000)


def test_many_open_images(window, qtbot, tmp_path):
    """Hundreds of files open at once as in MaxIm DL: a list with thumbnails, only the shown image is read; a
    process can run on all of them, the processed copies take their places and the originals stay unchanged."""
    from astrowb.io.fits import thumbnail

    paths = []
    for i in range(4):
        p = tmp_path / f"f{i}.fits"
        fits.PrimaryHDU(np.arange(1200, dtype=np.float32).reshape(30, 40) + 1000 * i).writeto(p)
        paths.append(str(p))
    assert thumbnail(paths[0], 8).shape == (6, 8)  # at most 8 pixels across, every 5th pixel
    page = window.image_page
    assert window.open_many(paths)
    assert page.open_paths() == paths and window.current_path.name == "f0.fits" and window.viewer.data[0, 0] == 0
    qtbot.waitUntil(lambda: not page.open_list.item(3).icon().isNull(), timeout=10000)
    window.next_action.trigger()
    assert window.current_path.name == "f1.fits" and window.viewer.data[0, 0] == 1000
    window.close_image()
    assert window.current_path.name == "f2.fits" and len(page.open_paths()) == 3
    window.apply_all_action.setChecked(True)
    window.process_image("flip", {"axis": "x"})
    qtbot.waitUntil(lambda: all("_flip" in p for p in page.open_paths()), timeout=60000)
    qtbot.waitUntil(lambda: window.current_path.name == "f2_flip.fits", timeout=10000)
    assert window.viewer.data[0, 0] == 2039 and fits.getdata(paths[2])[0, 0] == 2000
    window.apply_all_action.setChecked(False)
    window.close_image(everything=True)
    assert window.current_path is None and window.viewer.data is None and not page.open_paths()
    assert not window.process_menu.isEnabled()


def test_image_right_click_menu(window, tmp_path):
    """Right click on the image: measure the star, start photometry with it as the target, add comparisons,
    copy the position."""
    from PySide6.QtWidgets import QApplication

    yy, xx = np.mgrid[:60, :80]
    img = (
        100
        + 5000 * np.exp(-((xx - 30) ** 2 + (yy - 20) ** 2) / 4.0)
        + 3000 * np.exp(-((xx - 60) ** 2 + (yy - 40) ** 2) / 4.0)
    )
    paths = []
    for i in range(2):
        p = tmp_path / f"s{i}.fits"
        fits.PrimaryHDU(img.astype(np.float32), fits.Header({"DATE-OBS": f"2026-01-01T00:0{i}:00"})).writeto(p)
        paths.append(str(p))
    window.open_many(paths)
    menu = window.image_menu(30.0, 20.0)
    texts = [a.text() for a in menu.actions()]
    assert "Measure this star" in texts and "Zoom to &fit" in texts
    assert texts[0] == "Send the open images to Photometry"  # the plain way first, no star to choose
    menu.actions()[0].trigger()
    assert window.photometry_page.images == paths and window.current_workspace() == "photometry"
    window.photometry_page._clear()
    comp = next(a for a in menu.actions() if a.text() == "Photometry: add as a comparison star")
    assert not comp.isEnabled()  # no target yet
    next(a for a in menu.actions() if a.text() == "Measure this star").trigger()
    assert window.image_page.info.rowCount() > 3
    assert window.photometry_from_image(30.0, 20.0)
    phot = window.photometry_page
    assert phot.images == paths and phot.target == (30.0, 20.0) and window.current_workspace() == "photometry"
    comp = next(a for a in window.image_menu(60.0, 40.0).actions() if a.text() == comp.text())
    assert comp.isEnabled()
    comp.trigger()
    assert phot.comps == [(60.0, 40.0)]
    assert window._copy_position(29.0, 19.0) == "x=30.0 y=20.0" == QApplication.clipboard().text()


def test_every_button_and_menu_survives_empty_input(window, qtbot, monkeypatch):
    """A user clicking anything in any order with nothing chosen: no unhandled error (dialogs answer Cancel)."""
    import subprocess

    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QAbstractButton, QDialog, QFileDialog, QInputDialog, QMenu, QMessageBox

    for name, value in (
        ("getOpenFileName", ("", "")),
        ("getOpenFileNames", ([], "")),
        ("getSaveFileName", ("", "")),
        ("getExistingDirectory", ""),
    ):
        monkeypatch.setattr(QFileDialog, name, staticmethod(lambda *a, v=value, **k: v))
    for name in ("information", "warning", "critical", "about"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.Ok))
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.No))
    monkeypatch.setattr(QMessageBox, "exec", lambda self: QMessageBox.Cancel)
    for name in ("getText", "getItem", "getMultiLineText"):
        monkeypatch.setattr(QInputDialog, name, staticmethod(lambda *a, **k: ("", False)))
    monkeypatch.setattr(QInputDialog, "getDouble", staticmethod(lambda *a, **k: (0.0, False)))
    monkeypatch.setattr(QInputDialog, "getInt", staticmethod(lambda *a, **k: (0, False)))
    monkeypatch.setattr(QDialog, "exec", lambda self: 0)
    monkeypatch.setattr(QDesktopServices, "openUrl", staticmethod(lambda *a, **k: True))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no processes")))
    skip = ("Quit", "Exit", "Restart", "Tour", "tour", "Check for updates", "installation")
    clicked = 0
    for key, (_, page) in window.workspaces.items():
        window.show_workspace(key)
        for b in page.findChildren(QAbstractButton):
            if b.isEnabled() and b.isVisibleTo(page) and not any(s in b.text() for s in skip):
                b.click()
                clicked += 1
    for menu in window.menuBar().findChildren(QMenu):
        for a in menu.actions():
            if a.isEnabled() and not (a.menu() or a.isSeparator() or any(s in a.text() for s in skip)):
                a.trigger()
                clicked += 1
    assert clicked > 150  # pytest-qt fails the test on any exception raised in a slot


def test_pages_as_panels_beside_the_image(window, qtbot, tmp_path):
    """A page shown beside the image (as MaxIm DL's tool windows): the image stays, the sidebar brings the panel
    forward, closing the panel puts the page back; remembered for the next start."""
    from astrowb.ui.main_window import MainWindow

    window.show()
    window.show_workspace("image")
    dock = window.dock_page("photometry")
    assert dock.isVisible() and dock.widget() is window._frames[window.photometry_page]
    assert window.pages.indexOf(dock.widget()) == -1 and window.current_workspace() == "image"
    window.show_workspace("photometry")  # the sidebar raises the panel, the image stays
    assert window.current_workspace() == "image" and window.pages.currentWidget() is window._frames[window.image_page]
    window._fill_panels_menu()
    acts = {a.text(): a for a in window.panels_menu.actions()}
    assert acts[window._nav_items()["photometry"].text()].isChecked()
    acts[window._nav_items()["timeseries"].text()].trigger()  # a second panel, tabbed with the first
    assert set(window._panels) == {"photometry", "timeseries"}
    assert window.settings.get("ui.panels") == ["photometry", "timeseries"]
    again = MainWindow(window.settings)
    qtbot.addWidget(again)
    assert set(again._panels) == {"photometry", "timeseries"}
    again.engine.shutdown()
    dock.close()
    assert "photometry" not in window._panels and window.pages.indexOf(window._frames[window.photometry_page]) >= 0
    window.show_workspace("photometry")
    assert window.current_workspace() == "photometry"
    assert window.dock_page("image") is None and "image" not in window._panels


def test_borders_drag_and_the_image_follows_the_window(window, qtbot, fits_file):
    """Every border can be dragged: the header tabs beside the image fold away when their edge is dragged to the
    right, the sidebar's edge moves; the image stays fitted when its room or the window changes size."""
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest

    window.resize(1366, 768)
    window.show()
    window.open_fits(fits_file)
    page, viewer = window.image_page, window.viewer
    qtbot.waitUntil(lambda: viewer.width() > 100)
    before = viewer.width()

    def fitted():  # the whole image shown, touching two sides of the view
        rect, vp = viewer.mapFromScene(viewer.sceneRect()).boundingRect(), viewer.viewport()
        inside = rect.width() <= vp.width() + 2 and rect.height() <= vp.height() + 2
        return inside and (rect.width() >= vp.width() - 3 or rect.height() >= vp.height() - 3)

    assert fitted()
    handle = page.split.handle(1)
    QTest.mousePress(handle, Qt.LeftButton, pos=QPoint(2, 10))
    QTest.mouseMove(handle, QPoint(2 + page.width(), 10))  # drag the border to the right edge
    QTest.mouseRelease(handle, Qt.LeftButton, pos=QPoint(2 + page.width(), 10))
    qtbot.waitUntil(lambda: page.split.sizes()[1] == 0)  # the tabs folded away
    assert viewer.width() > before + 200 and fitted()  # more room, the image still fitted to it
    nav = window.central_split
    nav.setSizes([nav.sizes()[0] + 80, nav.sizes()[1] - 80])  # the sidebar's edge moves too
    assert window.nav.width() == nav.sizes()[0]
    big = viewer.transform().m11()
    window.resize(900, 600)  # a smaller window: the image shrinks with it, still whole
    qtbot.waitUntil(lambda: viewer.transform().m11() < big)
    assert fitted()


def test_photometry_star_picking(window, tmp_path):
    """A cross cursor with the aperture rings under the mouse, and a click on a marked star takes it off."""
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent

    yy, xx = np.mgrid[:60, :80]
    img = (
        100
        + 5000 * np.exp(-((xx - 30) ** 2 + (yy - 20) ** 2) / 4.0)
        + 3000 * np.exp(-((xx - 60) ** 2 + (yy - 40) ** 2) / 4.0)
    )
    p = tmp_path / "f.fits"
    fits.PrimaryHDU(img.astype(np.float32)).writeto(p)
    page = window.photometry_page
    page.set_images([str(p)])
    viewer = page.viewer
    assert page._lower.isHidden()  # nothing to show below the image yet: it has the whole height
    assert viewer.viewport().cursor().shape() == Qt.CrossCursor and len(viewer._hover_rings) == 3
    window.show()
    viewer.resize(400, 300)
    pos = viewer.mapFromScene(QPointF(31, 40))
    viewer.mouseMoveEvent(QMouseEvent(QMouseEvent.MouseMove, QPointF(pos), Qt.NoButton, Qt.NoButton, Qt.NoModifier))
    # the rings sit under the mouse (to the pixel rounding of the view)
    assert len([m for m in viewer._hover_items if m.data(0) is None]) == 3 and viewer._hover_items[
        0
    ].pos().x() == pytest.approx(31, abs=3)
    page._clicked(30.0, 20.0)
    page._clicked(60.0, 40.0)
    assert page.target == (30.0, 20.0) and page.comps == [(60.0, 40.0)]
    page._clicked(61.0, 40.5)  # on the comparison again: taken off, not marked twice
    assert page.comps == [] and len(viewer.marker_list) == 3
    # the lower panel (star table, light curve) came with the first star; Shift + wheel resizes the three rings
    assert not page._lower.isHidden()
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QWheelEvent

    r = (page.r_ap.value(), page.r_in.value(), page.r_out.value())
    wheel = QWheelEvent(QPointF(pos), QPointF(pos), QPoint(), QPoint(0, 120), Qt.NoButton, Qt.ShiftModifier,
                        Qt.NoScrollPhase, False)  # fmt: skip
    zoom = viewer.transform().m11()
    viewer.wheelEvent(wheel)
    assert (page.r_ap.value(), page.r_in.value(), page.r_out.value()) == tuple(v + 0.5 for v in r)
    assert viewer.transform().m11() == zoom  # the image kept its zoom
    assert viewer.marker_list[0][2] == r[0] + 0.5  # redrawn at the new size
    assert not page.show_what.isEnabled() and page.show_what.placeholderText()


def test_a_failed_lookup_is_reported_on_the_gui_thread(window, qtbot, tmp_path):
    """Target look-ups wrote their error into the Plan page from the task's callback, which runs on a background
    thread (a Qt widget touched from another thread can crash the application). on_fail runs on the GUI thread."""
    import threading

    got = []
    window.run_step(
        "calibration.scan",
        {"folder": str(tmp_path / "not-there")},
        on_fail=lambda msg: got.append((msg, threading.current_thread() is threading.main_thread())),
    )
    qtbot.waitUntil(lambda: bool(got), timeout=60000)
    assert "not-there" in got[0][0] and got[0][1]


def test_minimum_method_is_a_visible_choice_with_kvw_first(window):
    """Both methods are offered; eclipsing binaries (Kwee–van Woerden) are the default, transits one click away."""
    page = window.photometry_page
    sent = []
    page.minimum_requested.connect(lambda lc, params: sent.append(params["method"]))
    page.light_curve = {"time": [0.0, 1.0], "rel_flux": [1.0, 1.0]}
    assert page.kvw.isChecked() and not page.trapezoid.isChecked()
    page._minimum()
    page.trapezoid.setChecked(True)
    assert not page.kvw.isChecked()
    page._minimum()
    assert sent == ["kvw", "trapezoid"]
    page.plot.figure.clear()  # a result arriving when nothing is plotted (an intermittent CI failure)
    page.show_minimum({"time": 0.5, "error": 0.001, "time_scale": "BJD_TDB", "method": "kvw"})
    assert "Minimum: 0.500000" in page.result.text()


def test_light_curve_page_saves_for_the_models_page_and_warns_about_aliases(qtbot, tmp_path):
    from astrowb.models.data import read_light_curve
    from astrowb.ui.workspaces import PeriodPage

    page = PeriodPage()
    qtbot.addWidget(page)
    t = np.concatenate([np.linspace(0, 27, 300), np.linspace(700, 727, 300)])
    page.set_light_curve(t, 1 + 0.01 * np.sin(2 * np.pi * t / 0.3336), "W UMa (TESS 21, TESS 47)")
    page.save_csv(tmp_path / "lc.csv")
    tt, ff, _, _ = read_light_curve(tmp_path / "lc.csv")
    assert np.allclose(tt, t) and np.allclose(ff * np.median(page.flux), page.flux)
    page.show_result({"best": 0.3336, "periods": [], "power": []})
    text = page.result.text()  # one cycle more or less across the gap
    assert "700 d apart" in text and "0.333441 or 0.333759" in text
